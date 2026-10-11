"""The EuroEat recommendation agent.

A transparent, step-by-step pipeline. Every step emits an event so the UI can show
exactly how the agent reached its suggestions:

  1. understand   - parse the request (city, diet, meals, budget, extra context)
  2. identify     - find candidate restaurants in the city database (OpenStreetMap)
  3. shortlist    - score & shortlist per meal
  4. read_menu    - read each shortlisted restaurant's menu (scrape own site / estimate)
  5. translate    - translate menu items to English + classify vegetarian dishes (LLM)
  6. reviews      - read positive and negative reviews (translated)
  7. context      - semantic search over reviews for the user's specific context
  8. menu_items   - regular menu items + prices that fit the diet & meal
  9. suggest      - rank and explain final recommendations (LLM, streamed)
"""
import asyncio
import hashlib
import json
import math
import re
import time

from app import llm
from app.cities import CITIES, COUNTRIES, city_by_id, city_dict
from app.db import get_db, row_to_restaurant
from app.services import classify_veg, get_menu, get_reviews, guess_meal, links_for, save_menu_items

MEALS = ["breakfast", "lunch", "dinner"]
VEG_FRIENDLY_CUISINES = ("vegetarian", "vegan", "indian", "italian", "pizza", "mediterranean",
                         "falafel", "lebanese", "middle eastern", "thai", "mexican", "healthy",
                         "organic", "nepalese", "vietnamese", "greek", "salad", "juice", "brunch")

CONTEXT_QUERIES = {
    "vegetarian": "vegetarian options meat-free dishes",
    "vegan": "vegan dishes plant based",
    "gluten": "gluten-free coeliac celiac",
    "kids": "family friendly children kids menu high chair",
    "quiet": "quiet cosy atmosphere romantic",
    "budget": "good value cheap price set menu",
    "breakfast": "breakfast coffee pastries morning",
    "service": "service staff English speaking fast",
}

SYSTEM_INTENT = """You extract restaurant search intent for a travel food assistant in Europe.
Reply ONLY with JSON:
{"is_restaurant_search": bool, "city": string|null, "diet": "vegetarian"|"vegan"|"any",
 "meals": ["breakfast"|"lunch"|"dinner"], "budget": "low"|"mid"|"high"|null,
 "cuisines": [string], "context": [string], "party_size": int|null}
"context" are short keywords for the user's specific needs that reviews could confirm,
e.g. "gluten-free", "kids", "quiet", "cheap", "vegan", "near the beach".
If meals are not mentioned use all three. If diet is not mentioned use "vegetarian"."""


def _ev(step, status, title, detail="", data=None):
    return {"type": "step", "step": step, "status": status, "title": title, "detail": detail,
            "data": data or {}}


def _keyword_intent(q: str) -> dict:
    ql = q.lower()
    city = next((c[0] for c in CITIES if c[1].lower() in ql or c[0] in ql), None)
    meals = [m for m in MEALS if m in ql] or (["breakfast"] if "brunch" in ql else []) or MEALS
    diet = "vegan" if "vegan" in ql else ("any" if re.search(r"non[- ]?veg|meat|any food", ql) else "vegetarian")
    ctx = [k for k in ("gluten", "kids", "quiet", "cheap", "romantic", "family", "budget", "vegan")
           if k in ql]
    budget = "low" if any(w in ql for w in ("cheap", "budget", "affordable")) else (
        "high" if any(w in ql for w in ("fine dining", "luxury", "michelin")) else None)
    return {"is_restaurant_search": bool(city) or any(w in ql for w in ("restaurant", "eat", "food", "meal")),
            "city": city, "diet": diet, "meals": meals, "budget": budget, "cuisines": [],
            "context": ctx, "party_size": None}


def _resolve_city(name: str | None) -> str | None:
    if not name:
        return None
    n = name.lower().strip()
    aliases = {"sevilla": "seville", "roma": "rome", "milano": "milan", "firenze": "florence",
               "venezia": "venice", "münchen": "munich", "lisboa": "lisbon", "praha": "prague",
               "wien": "vienna", "bruxelles": "brussels", "kraków": "krakow", "zürich": "zurich",
               "københavn": "copenhagen", "athina": "athens"}
    n = aliases.get(n, n)
    for c in CITIES:
        if c[0] == n or c[1].lower() == n or c[1].lower() in n:
            return c[0]
    return None


async def understand(query: str, overrides: dict) -> dict:
    kw = _keyword_intent(query)
    intent = None
    if query.strip():
        intent = await llm.chat_json([{"role": "system", "content": SYSTEM_INTENT},
                                      {"role": "user", "content": query}], timeout=60)
    if not isinstance(intent, dict):
        intent, method = kw, "keyword rules (LLM unavailable)"
    else:
        method = f"LLM ({llm.MODEL})"
        intent["city"] = _resolve_city(intent.get("city")) or kw["city"]
        intent["meals"] = [m for m in (intent.get("meals") or []) if m in MEALS] or kw["meals"]
        if intent.get("diet") not in ("vegetarian", "vegan", "any"):
            intent["diet"] = kw["diet"]
        if kw["city"] or kw["context"]:
            intent["is_restaurant_search"] = True
        intent["context"] = list(dict.fromkeys((intent.get("context") or []) + kw["context"]))[:5]
        intent["cuisines"] = [c for c in (intent.get("cuisines") or []) if isinstance(c, str)][:3]
    if not query.strip() and overrides:
        method = "your assisted-search selections"
    for k, v in (overrides or {}).items():
        if v not in (None, "", []):
            intent[k] = v
    if overrides.get("city"):
        intent["is_restaurant_search"] = True
    intent["method"] = method
    return intent


def _meal_ok(r: dict, meal: str) -> bool:
    oh = (r.get("opening_hours") or "").lower()
    times = re.findall(r"(\d{1,2}):\d{2}", oh)
    hours = [int(t) for t in times]
    if meal == "breakfast":
        return bool(r["breakfast"]) or (hours and min(hours) <= 9 and r["amenity"] != "fast_food")
    if r["amenity"] == "cafe" and not r.get("cuisine"):
        return False
    if meal == "lunch":
        return not hours or min(hours) <= 13
    # dinner
    return r["amenity"] != "cafe" and (not hours or max(hours) >= 21 or 0 in hours or 1 in hours)


def _veg_strength(r: dict) -> int:
    if r.get("diet_vegetarian") == "only" or r.get("diet_vegan") == "only":
        return 3
    if r.get("diet_vegetarian") == "yes" or r.get("diet_vegan") == "yes":
        return 2
    cuisine = (r.get("cuisine") or "").lower()
    if any(c in cuisine for c in VEG_FRIENDLY_CUISINES):
        return 1
    return 0


def _dist_km(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110.57
    return math.hypot(dx, dy)


def _jitter(rid: str) -> float:
    return (int(hashlib.md5(rid.encode()).hexdigest(), 16) % 1000) / 1000


def _shortlist_score(r: dict, intent: dict, city: dict) -> float:
    s = 0.0
    if intent["diet"] in ("vegetarian", "vegan"):
        s += _veg_strength(r) * 1.6
        if intent["diet"] == "vegan" and r.get("diet_vegan") in ("yes", "only"):
            s += 1.5
    s += 1.5 if r.get("website") else 0
    s += 1.0 if r.get("menu_url") else 0
    cuisine = (r.get("cuisine") or "").lower()
    if any(c.lower() in cuisine for c in intent.get("cuisines") or []):
        s += 2
    if intent.get("budget") == "low":
        s += (3 - (r.get("price_level") or 2)) * 0.6
    elif intent.get("budget") == "high":
        s += ((r.get("price_level") or 2) - 2) * 0.6
    s -= _dist_km(r["lat"], r["lon"], city["lat"], city["lon"]) * 0.35
    return s + _jitter(r["id"]) * 0.8


async def translate_cached(texts: list[str], lang: str, chunk=12) -> tuple[dict, dict]:
    """Translate unique strings to English, using the SQLite translation cache first.
    Returns ({text: english}, {"cached": n, "llm": n, "failed": n})."""
    uniq = list(dict.fromkeys(t for t in texts if t))
    out, stats = {}, {"cached": 0, "llm": 0, "failed": 0}
    if lang == "en":
        return {t: t for t in uniq}, stats
    with get_db() as db:
        for t in uniq:
            row = db.execute("SELECT en FROM translations WHERE src_lang=? AND src=?", (lang, t)).fetchone()
            if row:
                out[t] = row["en"]
                stats["cached"] += 1
    todo = [t for t in uniq if t not in out]
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        res = await llm.translate_batch(part, lang)
        if not res:
            stats["failed"] += len(part)
            continue
        stats["llm"] += len(part)
        with get_db() as db:
            for src, en in zip(part, res):
                out[src] = en
                db.execute("INSERT OR REPLACE INTO translations VALUES (?,?,?)", (lang, src, en))
    return out, stats


def _display_items(items: list[dict], meal: str, diet: str, n=8) -> list[dict]:
    if diet in ("vegetarian", "vegan"):
        items = [it for it in items if it.get("vegetarian")]
    fit = [it for it in items if it.get("meal") in (meal, "any")] or items
    if meal == "breakfast":
        fit = sorted(fit, key=lambda it: it.get("meal") != "breakfast")
    return fit[:n]


def _merge_stats(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


async def _translate_reviews(reviews: list[dict]) -> dict:
    stats = {}
    by_lang = {}
    for r in reviews:
        if r["lang"] != "en" and not r.get("_translated"):
            by_lang.setdefault(r["lang"], []).append(r)
    split = lambda t: [s for s in re.split(r"(?<=[.!?])\s+", t) if s]  # noqa: E731
    for lang, rs in by_lang.items():
        # sentence-level translation: better cache reuse and shorter LLM outputs
        got, st = await translate_cached([s for r in rs for s in split(r["text"])], lang, chunk=8)
        stats = _merge_stats(stats, st)
        for r in rs:
            parts = [got.get(s) for s in split(r["text"])]
            if parts and all(parts):
                r["text_en"] = " ".join(parts)
                r["_translated"] = True
    return stats


async def _context_search(reviews: list[dict], queries: list[str]) -> tuple[list[dict], str]:
    if not queries or not reviews:
        return [], "no context"
    texts = [r["text_en"] for r in reviews]
    embs = await llm.embed(queries + texts)
    matches = []
    if embs:
        qv, rv = embs[:len(queries)], embs[len(queries):]
        for r, v in zip(reviews, rv):
            best = max(range(len(queries)), key=lambda i: llm.cosine(qv[i], v))
            score = llm.cosine(qv[best], v)
            if score >= 0.62:
                matches.append({**r, "query": queries[best], "similarity": round(score, 3)})
        method = f"semantic search ({llm.EMBED_MODEL} embeddings)"
    else:
        for r in reviews:
            for q in queries:
                words = [w for w in q.split() if len(w) > 3]
                if any(w.lower()[:6] in r["text_en"].lower() for w in words):
                    matches.append({**r, "query": q, "similarity": None})
                    break
        method = "keyword search"
    matches.sort(key=lambda m: -(m["similarity"] or 0))
    return matches[:4], method


def _context_queries(intent: dict) -> list[str]:
    qs = []
    if intent["diet"] in ("vegetarian", "vegan"):
        qs.append(CONTEXT_QUERIES[intent["diet"]])
    if "breakfast" in intent["meals"]:
        qs.append(CONTEXT_QUERIES["breakfast"])
    for c in intent.get("context") or []:
        cl = c.lower()
        key = next((k for k in CONTEXT_QUERIES if k in cl), None)
        if key is None:
            key = {"cheap": "budget", "family": "kids", "child": "kids", "romantic": "quiet",
                   "celiac": "gluten", "coeliac": "gluten"}.get(next((w for w in
                   ("cheap", "family", "child", "romantic", "celiac", "coeliac") if w in cl), ""), None)
        qs.append(CONTEXT_QUERIES[key] if key else c)
    return list(dict.fromkeys(qs))[:4]


def _brief(r):
    return {k: r[k] for k in ("author", "rating", "lang", "text", "text_en", "source", "created_at")} | (
        {"query": r["query"], "similarity": r["similarity"]} if "query" in r else {})


async def run_agent(query: str, overrides: dict | None = None):
    overrides = overrides or {}
    t0 = time.time()

    # 1. understand ---------------------------------------------------------
    yield _ev("understand", "running", "Understanding your request")
    intent = await understand(query, overrides)
    if not intent.get("is_restaurant_search") and not intent.get("city"):
        yield _ev("understand", "done", "This looks like a general question", intent["method"], intent)
        yield {"type": "answer_start"}
        got = False
        async for chunk in llm.chat_stream([
            {"role": "system", "content": "You are EuroEat, a friendly assistant for travellers eating "
             "out in Europe (with a focus on vegetarian food). Answer concisely in markdown."},
            {"role": "user", "content": query}]):
            got = True
            yield {"type": "token", "text": chunk}
        if not got:
            yield {"type": "token", "text": "I can recommend restaurants in 32 European cities. Try: "
                   "*\"Vegetarian lunch and dinner in Barcelona, gluten-free\"*."}
        yield {"type": "done", "elapsed": round(time.time() - t0, 1)}
        return
    if not intent.get("city"):
        yield _ev("understand", "done", "I need a city", intent["method"], intent)
        yield {"type": "clarify", "message": "Which city are you travelling to? I currently cover: "
               + ", ".join(c[1] for c in CITIES) + "."}
        yield {"type": "done", "elapsed": round(time.time() - t0, 1)}
        return
    city = city_dict(city_by_id(intent["city"]))
    lang_name = llm.LANG_NAMES.get(city["lang"], city["lang"])
    yield _ev("understand", "done",
              f"{intent['diet'].title()} · {', '.join(intent['meals'])} · {city['name']}, {city['country']}",
              f"Parsed with {intent['method']}. Extra context: {', '.join(intent.get('context') or []) or 'none'}",
              {"intent": intent, "city": city})

    # 2. identify -----------------------------------------------------------
    yield _ev("identify", "running", f"Searching restaurants in {city['name']}")
    with get_db() as db:
        rows = [row_to_restaurant(r) for r in db.execute(
            "SELECT * FROM restaurants WHERE city_id=?", (city["id"],))]
    total = len(rows)
    if intent["diet"] in ("vegetarian", "vegan"):
        cands = [r for r in rows if _veg_strength(r) > 0]
    else:
        cands = rows
    per_meal = {m: [r for r in cands if _meal_ok(r, m)] for m in intent["meals"]}
    tagged = sum(1 for r in cands if _veg_strength(r) >= 2)
    yield _ev("identify", "done",
              f"{len(cands):,} of {total:,} places match the {intent['diet']} filter",
              f"{tagged} are explicitly tagged vegetarian/vegan on OpenStreetMap, the rest serve "
              f"veg-friendly cuisines. " + " · ".join(f"{m}: {len(v):,}" for m, v in per_meal.items()),
              {"total": total, "candidates": len(cands), "per_meal": {m: len(v) for m, v in per_meal.items()}})
    if not cands:
        yield {"type": "clarify", "message": f"I don't have {intent['diet']} places for {city['name']} yet. "
               "Run the OSM ingester for this city."}
        yield {"type": "done", "elapsed": round(time.time() - t0, 1)}
        return

    # 3. shortlist ----------------------------------------------------------
    yield _ev("shortlist", "running", "Scoring and shortlisting")
    k = 4 if len(intent["meals"]) > 1 else 6
    shortlist, used = {}, set()
    for meal in intent["meals"]:
        ranked = sorted(per_meal[meal], key=lambda r: -_shortlist_score(r, intent, city))
        picks = [r for r in ranked if r["id"] not in used][:k]
        used.update(r["id"] for r in picks)
        shortlist[meal] = picks
    uniq = {r["id"]: r for picks in shortlist.values() for r in picks}
    yield _ev("shortlist", "done", f"Shortlisted {len(uniq)} restaurants",
              "Score = vegetarian tag strength + has website/menu link + cuisine & budget fit "
              "- distance from the centre",
              {"shortlist": {m: [{"id": r["id"], "name": r["name"], "cuisine": r["cuisine"],
                                  "veg_tag": r["diet_vegetarian"] or r["diet_vegan"],
                                  "distance_km": round(_dist_km(r["lat"], r["lon"], city["lat"], city["lon"]), 2)}
                                 for r in picks] for m, picks in shortlist.items()}})

    # 4. read menus ---------------------------------------------------------
    yield _ev("read_menu", "running", f"Reading {len(uniq)} menus",
              "Visiting each restaurant's own website (httpx, Playwright for JS sites, PDF parsing)")
    sem = asyncio.Semaphore(4)
    menus = {}

    async def load(r):
        async with sem:
            try:
                menus[r["id"]] = await asyncio.wait_for(get_menu(r), timeout=35)
            except Exception:
                menus[r["id"]] = await get_menu(r, scrape=False)

    await asyncio.gather(*(load(r) for r in uniq.values()))
    scraped = [rid for rid, m in menus.items() if m["source"] == "scraped"]
    yield _ev("read_menu", "done",
              f"{len(scraped)} menus scraped live, {len(menus) - len(scraped)} estimated",
              "Estimated menus are built from regional dishes when a site is missing, down or has no "
              "readable prices.",
              {"menus": {uniq[rid]["name"]: {"source": m["source"], "items": len(m["items"]),
                                             "page": m.get("menu_page") or m.get("source_url"),
                                             "note": m.get("note")} for rid, m in menus.items()}})

    # 5. translate ----------------------------------------------------------
    yield _ev("translate", "running", f"Translating menus from {lang_name}",
              "Only the dishes that fit your diet and meal are sent to the LLM; translations are cached")
    meal_of = {r["id"]: meal for meal, picks in shortlist.items() for r in picks}
    by_lang = {}
    for rid, m in menus.items():
        for it in _display_items(m["items"], meal_of[rid], intent["diet"], n=10):
            by_lang.setdefault(m["lang"], []).append(it["name"])
    tstats, tmap = {}, {}
    for lang, names in by_lang.items():
        got, st = await translate_cached(names, lang)
        tmap[lang] = got
        tstats = _merge_stats(tstats, st)
    examples = []
    for rid, m in menus.items():
        veg_rest = uniq[rid].get("diet_vegetarian") == "only" or uniq[rid].get("diet_vegan") == "only"
        for it in m["items"]:
            en = tmap.get(m["lang"], {}).get(it["name"])
            it["name_en"] = en or it.get("name_en") or it.get("gloss_en") or it["name"]
            if m["source"] == "scraped":  # re-check diet & meal on original + English text
                it["vegetarian"] = classify_veg(it["name"] + " " + it["name_en"], veg_rest)
                if it.get("meal") in (None, "any"):
                    it["meal"] = guess_meal(it["name"] + " " + it["name_en"])
            if en and en.lower() != it["name"].lower() and len(examples) < 10:
                examples.append({"original": it["name"], "english": en, "restaurant": uniq[rid]["name"]})
        save_menu_items(rid, m["items"])
    tmethod = (f"LLM ({llm.MODEL}): {tstats.get('llm', 0)} new, {tstats.get('cached', 0)} from cache"
               + (f", {tstats['failed']} fell back to glossary" if tstats.get("failed") else ""))
    yield _ev("translate", "done", f"Translated {sum(len(v) for v in tmap.values())} menu items to English",
              f"{tmethod}. Vegetarian dishes detected with multilingual meat/fish keyword rules.",
              {"examples": examples})

    # 6. reviews ------------------------------------------------------------
    yield _ev("reviews", "running", "Reading positive and negative reviews")
    reviews = {rid: get_reviews(r) for rid, r in uniq.items()}
    all_revs = [rv for rs in reviews.values() for rv in rs]
    shown = [rv for rs in reviews.values() for rv in
             ([x for x in rs if x["rating"] >= 4][:2] + [x for x in rs if x["rating"] <= 2][:2])]
    rstats = await _translate_reviews(shown)
    rmethod = f"LLM ({llm.MODEL}): {rstats.get('llm', 0)} new, {rstats.get('cached', 0)} cached"
    pos = sum(1 for rv in all_revs if rv["rating"] >= 4)
    neg = sum(1 for rv in all_revs if rv["rating"] <= 2)
    sample_pos = next((rv for rv in all_revs if rv["rating"] >= 4 and rv["lang"] != "en"), None)
    sample_neg = next((rv for rv in all_revs if rv["rating"] <= 2), None)
    yield _ev("reviews", "done", f"Read {len(all_revs)} reviews: {pos} positive, {neg} negative",
              f"Non-English reviews translated with {rmethod}. Source: sample review dataset.",
              {"positive_sample": sample_pos and _brief(sample_pos),
               "negative_sample": sample_neg and _brief(sample_neg)})

    # 7. context search -----------------------------------------------------
    queries = _context_queries(intent)
    yield _ev("context", "running", "Searching reviews for your specific needs",
              "Queries: " + "; ".join(queries))
    ctx = {}
    cmethod = "n/a"
    for rid, rs in reviews.items():
        ctx[rid], cmethod = await _context_search(rs, queries)
    # matches are copies of review dicts: translate them so the user sees English
    await _translate_reviews([c for v in ctx.values() for c in v])
    hits = sum(len(v) for v in ctx.values())
    yield _ev("context", "done", f"Found {hits} reviews relevant to your context", f"Method: {cmethod}",
              {"queries": queries})

    # 8. menu items -----------------------------------------------------------
    yield _ev("menu_items", "running", "Picking regular menu items and prices")
    results = {}
    for meal, picks in shortlist.items():
        out = []
        for r in picks:
            m = menus[r["id"]]
            fit = _display_items(m["items"], meal, intent["diet"], n=10)
            rs = reviews[r["id"]]
            rating = round(sum(x["rating"] for x in rs) / len(rs), 1) if rs else None
            ctx_pos = [c for c in ctx[r["id"]] if c["rating"] >= 4]
            ctx_neg = [c for c in ctx[r["id"]] if c["rating"] <= 2]
            score = ((rating or 3) * 1.2 + min(len(fit), 8) * 0.25 + len(ctx_pos) * 0.6
                     - len(ctx_neg) * 0.8 + (0.4 if m["source"] == "scraped" else 0)
                     + _veg_strength(r) * 0.3)
            prices = [it["price"] for it in fit[:6] if it.get("price")]
            out.append({
                "id": r["id"], "name": r["name"], "cuisine": r["cuisine"], "amenity": r["amenity"],
                "address": r["address"], "lat": r["lat"], "lon": r["lon"], "phone": r["phone"],
                "opening_hours": r["opening_hours"], "veg_tag": r["diet_vegetarian"],
                "vegan_tag": r["diet_vegan"], "price_level": r["price_level"],
                "rating": rating, "review_count": len(rs),
                "links": links_for(r, m.get("menu_page")),
                "menu": {"source": m["source"], "note": m.get("note"), "lang": m["lang"],
                         "pdf": m.get("pdf"), "items": fit[:8]},
                "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
                "currency": city["currency"],
                "positive": [_brief(x) for x in rs if x["rating"] >= 4][:2],
                "negative": [_brief(x) for x in rs if x["rating"] <= 2][:2],
                "context_matches": [_brief(x) for x in ctx[r["id"]]],
                "score": round(score, 2),
                "distance_km": round(_dist_km(r["lat"], r["lon"], city["lat"], city["lon"]), 2),
            })
        out.sort(key=lambda x: -x["score"])
        results[meal] = out[:3]
    n_items = sum(len(x["menu"]["items"]) for v in results.values() for x in v)
    yield _ev("menu_items", "done", f"Selected {n_items} {intent['diet']} dishes with prices",
              "Ranking = review rating + matching dishes + context-positive reviews - context-negative "
              "reviews + live-menu bonus")

    # 9. suggest ------------------------------------------------------------
    yield {"type": "results", "city": city, "intent": intent, "recommendations": results}
    yield _ev("suggest", "running", "Writing personalised suggestions")
    summary = {meal: [{"name": x["name"], "cuisine": x["cuisine"], "rating": x["rating"],
                       "dishes": [f"{d.get('name_en') or d['name']} ({d['price']} {d['currency']})"
                                  for d in x["menu"]["items"][:3]],
                       "praise": [c["text_en"][:120] for c in x["context_matches"] if c["rating"] >= 4][:1],
                       "warning": [n["text_en"][:120] for n in x["negative"]][:1]}
                      for x in v] for meal, v in results.items()}
    yield {"type": "answer_start"}
    got = False
    async for chunk in llm.chat_stream([
        {"role": "system", "content": (
            "You are EuroEat, a concise travel food agent. Using ONLY the JSON data provided, write a "
            "short markdown recommendation: for each meal, a heading and the top pick in bold with 1-2 "
            "dishes and prices, why (cite review praise), one caveat from negative reviews, and a "
            "one-line alternative. Under 220 words. Do not invent restaurants or prices.")},
        {"role": "user", "content": f"User request: {query or json.dumps(overrides)}\n"
                                    f"City: {city['name']}. Diet: {intent['diet']}.\n"
                                    f"Data: {json.dumps(summary, ensure_ascii=False)}"}]):
        got = True
        yield {"type": "token", "text": chunk}
    if not got:
        for meal, v in results.items():
            if not v:
                continue
            top = v[0]
            dishes = ", ".join(f"{d.get('name_en') or d['name']} ({d['price']} {d['currency']})"
                               for d in top["menu"]["items"][:2])
            alt = f" Alternative: **{v[1]['name']}**." if len(v) > 1 else ""
            yield {"type": "token", "text": f"### {meal.title()}\n**{top['name']}** "
                   f"({top['rating']}★) — try {dishes}.{alt}\n\n"}
    yield _ev("suggest", "done", "Recommendations ready", f"Total time {round(time.time() - t0, 1)}s")
    yield {"type": "done", "elapsed": round(time.time() - t0, 1)}
