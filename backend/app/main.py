import asyncio
import re
import datetime as dt
import json
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import llm
from app.agent.pipeline import _veg_strength, run_agent
from app.auth import authenticate, current_user, ensure_demo_user
from app.buildings import get_buildings
from app.cities import CITIES, COUNTRIES, city_by_id, city_dict
from app.coupons import evaluate
from app.db import dumps, get_db, init_db, row_to_restaurant
from app.services import get_menu, get_reviews, links_for

app = FastAPI(title="EuroEat Agent API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    init_db()
    ensure_demo_user()


# ---------------------------------------------------------------- auth / user
class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginIn):
    token = authenticate(body.username.strip(), body.password)
    if not token:
        raise HTTPException(401, "Invalid login ID or password")
    return {"token": token, "user": _user(body.username.strip())}


def _user(username: str) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        n_orders = db.execute("SELECT count(*) FROM orders WHERE username=?", (username,)).fetchone()[0]
    if not row:
        raise HTTPException(404)
    d = dict(row)
    for k in ("password_hash", "salt"):
        d.pop(k)
    d["settings"] = json.loads(d.pop("settings_json") or "{}")
    d["orders"] = n_orders
    return d


@app.get("/api/me")
def me(user: str = Depends(current_user)):
    return _user(user)


class ProfileIn(BaseModel):
    full_name: str | None = None
    email: str | None = None
    home_city: str | None = None
    diet: str | None = None
    settings: dict | None = None


@app.put("/api/me")
def update_me(body: ProfileIn, user: str = Depends(current_user)):
    with get_db() as db:
        for f in ("full_name", "email", "home_city", "diet"):
            v = getattr(body, f)
            if v is not None:
                db.execute(f"UPDATE users SET {f}=? WHERE username=?", (v, user))
        if body.settings is not None:
            db.execute("UPDATE users SET settings_json=? WHERE username=?", (dumps(body.settings), user))
    return _user(user)


# ---------------------------------------------------------------- catalog
@app.get("/api/health")
async def health():
    with get_db() as db:
        n = db.execute("SELECT count(*) FROM restaurants").fetchone()[0]
    return {"ok": True, "restaurants": n, "llm": await llm.status()}


def _city_counts():
    with get_db() as db:
        return {r["city_id"]: dict(r) for r in db.execute(
            """SELECT city_id, count(*) total,
                      sum(diet_vegetarian IN ('yes','only') OR diet_vegan IN ('yes','only')) veg_tagged,
                      sum(breakfast) breakfast
               FROM restaurants GROUP BY city_id""")}


@app.get("/api/countries")
def countries(user: str = Depends(current_user)):
    counts = _city_counts()
    out = []
    for cc, c in COUNTRIES.items():
        cities = [x for x in CITIES if x[2] == cc]
        out.append({"code": cc, **c, "cities": len(cities),
                    "restaurants": sum(counts.get(x[0], {}).get("total", 0) for x in cities)})
    return sorted(out, key=lambda x: x["name"])


@app.get("/api/cities")
def cities(country: str | None = None, user: str = Depends(current_user)):
    counts = _city_counts()
    return [{**city_dict(c), "restaurants": counts.get(c[0], {}).get("total", 0),
             "veg_tagged": counts.get(c[0], {}).get("veg_tagged", 0)}
            for c in CITIES if not country or c[2] == country]


# ---------------------------------------------------------------- agent
class AgentIn(BaseModel):
    query: str = ""
    overrides: dict = {}


@app.post("/api/agent/stream")
async def agent_stream(body: AgentIn, user: str = Depends(current_user)):
    async def gen():
        try:
            async for ev in run_agent(body.query, body.overrides):
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # surface errors to the UI instead of a dead stream
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- restaurants
def _rest(rid: str) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM restaurants WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Restaurant not found")
    return row_to_restaurant(row)


@app.get("/api/restaurants/{rid:path}")
async def restaurant(rid: str, user: str = Depends(current_user)):
    r = _rest(rid)
    menu = await get_menu(r)
    reviews = get_reviews(r)
    return {**r, "links": links_for(r, menu.get("menu_page")), "menu": menu, "reviews": reviews,
            "city": city_dict(city_by_id(r["city_id"]))}


# ---------------------------------------------------------------- coupons / orders
class CouponIn(BaseModel):
    restaurant_id: str
    kind: str
    meal: str
    subtotal: float


@app.post("/api/coupons/evaluate")
def coupons(body: CouponIn, user: str = Depends(current_user)):
    return evaluate(_rest(body.restaurant_id), body.kind, body.meal, body.subtotal)


class OrderItem(BaseModel):
    name: str
    price: float
    qty: int = 1


class OrderIn(BaseModel):
    restaurant_id: str
    kind: str                       # order_online | dine_in
    meal: str
    items: list[OrderItem] = []
    party_size: int = 2
    slot: str | None = None
    coupon: str | None = "auto"     # "auto" -> best coupon


def _place(user: str, body: OrderIn, auto=False) -> dict:
    r = _rest(body.restaurant_id)
    city = city_dict(city_by_id(r["city_id"]))
    subtotal = round(sum(i.price * i.qty for i in body.items), 2)
    ev = evaluate(r, body.kind, body.meal, subtotal)
    chosen = None
    if body.coupon == "auto":
        chosen = ev["best"]
    elif body.coupon:
        chosen = next((c for c in ev["all"] if c["code"] == body.coupon and c["applicable"]), None)
    discount = chosen["discount"] if chosen else 0
    delivery = 3.5 if body.kind == "order_online" else 0
    total = round(max(subtotal - discount, 0) + delivery, 2)
    slot = body.slot or {"breakfast": "09:00", "lunch": "13:30", "dinner": "20:30"}.get(body.meal, "20:00")
    oid = ("ORD-" if body.kind == "order_online" else "BKG-") + secrets.token_hex(3).upper()
    order = {"id": oid, "restaurant_id": r["id"], "restaurant": r["name"], "kind": body.kind,
             "meal": body.meal, "items": [i.model_dump() for i in body.items], "party_size": body.party_size,
             "slot": slot, "coupon": chosen, "subtotal": subtotal, "discount": discount,
             "delivery_fee": delivery, "total": total, "currency": city["currency"],
             "status": "confirmed (simulated)", "auto": auto,
             "eta": "35-45 min" if body.kind == "order_online" else None,
             "created_at": dt.datetime.now().isoformat(timespec="seconds"),
             "links": links_for(r)}
    with get_db() as db:
        db.execute("INSERT INTO orders (id, username, restaurant_id, kind, meal, items_json, party_size, slot, "
                   "coupon, subtotal, discount, total, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (oid, user, r["id"], body.kind, body.meal, dumps(order["items"]), body.party_size, slot,
                    chosen["code"] if chosen else None, subtotal, discount, total, order["status"]))
    return order


@app.post("/api/orders")
def place_order(body: OrderIn, user: str = Depends(current_user)):
    if body.kind == "order_online" and not body.items:
        raise HTTPException(400, "Add at least one item")
    return _place(user, body)


DRINK_WORDS = re.compile(
    r"\b(kombucha|lemonade|limonada|juice|zumo|suc|soda|cola|water|agua|aigua|beer|cerveza|cervesa|bière|"
    r"birra|bier|wine|vino|vi|vin|wein|cava|prosecco|champagne|cocktail|vermut|vermouth|sangria|gin|"
    r"whisky|vodka|rum|spritz|inedit|estrella|moritz|mahou|smoothie|batido|tea|té|te|infusion|refresco|"
    r"mojito|margarita|caipirinha|negroni|daiquiri|aperol|sake|soju|sidra|cider|ale|lager|ipa|martini)\b",
    re.I)


class AutoIn(BaseModel):
    restaurant_id: str
    kind: str
    meal: str
    party_size: int = 2
    diet: str = "vegetarian"
    slot: str | None = None


@app.post("/api/orders/auto")
async def auto_order(body: AutoIn, user: str = Depends(current_user)):
    """Agent places the order / booking on its own: picks dishes and the best coupon."""
    r = _rest(body.restaurant_id)
    menu = await get_menu(r, scrape=False)
    items = menu["items"]
    if body.diet in ("vegetarian", "vegan"):
        items = [i for i in items if i.get("vegetarian")]
    fit = [i for i in items if i.get("meal") in (body.meal, "any")] or items
    # the agent orders food, not drinks; and never alcohol on the traveller's behalf
    food = [i for i in fit if not DRINK_WORDS.search(f"{i['name']} {i.get('name_en') or ''}")]
    fit = sorted(food or fit, key=lambda i: i["price"])
    picks = []
    # one main-ish dish per person + one item to share, mid-priced first
    mid = fit[len(fit) // 3:] + fit[:len(fit) // 3]
    for i in range(min(body.party_size + 1, len(mid))):
        it = mid[i]
        picks.append(OrderItem(name=it.get("name_en") or it["name"], price=it["price"], qty=1))
    order = _place(user, OrderIn(restaurant_id=r["id"], kind=body.kind, meal=body.meal,
                                 items=picks, party_size=body.party_size, slot=body.slot, coupon="auto"),
                   auto=True)
    order["agent_note"] = (f"Picked {len(picks)} {body.diet} dishes for {body.party_size} "
                           f"and applied the best available coupon automatically.")
    return order


@app.get("/api/orders")
def orders(user: str = Depends(current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT o.*, r.name restaurant, r.city_id FROM orders o LEFT JOIN restaurants r "
            "ON r.id=o.restaurant_id WHERE username=? ORDER BY created_at DESC", (user,)).fetchall()
    return [{**dict(r), "items": json.loads(r["items_json"])} for r in rows]


# ---------------------------------------------------------------- stats / 3D map
@app.get("/api/stats/overview")
def stats_overview(user: str = Depends(current_user)):
    counts = _city_counts()
    cities_out = []
    for c in CITIES:
        cc = counts.get(c[0], {})
        cities_out.append({**city_dict(c), "total": cc.get("total", 0), "veg_tagged": cc.get("veg_tagged", 0),
                           "breakfast": cc.get("breakfast", 0)})
    per_country = {}
    for c in cities_out:
        pc = per_country.setdefault(c["country_code"], {"code": c["country_code"], "name": c["country"],
                                                         "total": 0, "veg_tagged": 0, "cities": 0})
        pc["total"] += c["total"]
        pc["veg_tagged"] += c["veg_tagged"]
        pc["cities"] += 1
    with get_db() as db:
        cuisines = db.execute(
            "SELECT cuisine, count(*) n FROM restaurants WHERE cuisine IS NOT NULL "
            "GROUP BY cuisine ORDER BY n DESC LIMIT 10").fetchall()
        menus = db.execute("SELECT source, count(*) n FROM menus GROUP BY source").fetchall()
    return {"total": sum(c["total"] for c in cities_out),
            "veg_tagged": sum(c["veg_tagged"] for c in cities_out),
            "countries": sorted(per_country.values(), key=lambda x: -x["total"]),
            "cities": cities_out,
            "top_cuisines": [dict(r) for r in cuisines],
            "menus": {r["source"]: r["n"] for r in menus}}


@app.get("/api/stats/city/{city_id}")
def city_points(city_id: str, user: str = Depends(current_user)):
    c = city_by_id(city_id)
    if not c:
        raise HTTPException(404)
    with get_db() as db:
        rows = db.execute("SELECT * FROM restaurants WHERE city_id=?", (city_id,)).fetchall()
    pts = [[r["id"], r["name"], round(r["lat"], 6), round(r["lon"], 6), _veg_strength(dict(r)),
            r["amenity"], r["cuisine"]] for r in rows]
    return {"city": city_dict(c), "points": pts}


@app.get("/api/stats/lookup")
async def lookup_place(q: str, user: str = Depends(current_user)):
    """Check whether any city/town in Europe has restaurant options (live, via OSM)."""
    q = q.strip()
    for c in CITIES:
        if c[1].lower() == q.lower() or c[0] == q.lower():
            counts = _city_counts().get(c[0], {})
            return {**city_dict(c), "in_catalog": True, "total": counts.get("total", 0),
                    "veg_tagged": counts.get("veg_tagged", 0)}
    import httpx
    from app.ingest.osm import HEADERS, overpass
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        r = await client.get("https://nominatim.openstreetmap.org/search",
                             params={"q": q, "format": "json", "limit": 1, "addressdetails": 1,
                                     "accept-language": "en"})
        hits = r.json() if r.status_code == 200 else []
    if not hits:
        raise HTTPException(404, f"Could not find '{q}'")
    h = hits[0]
    lat, lon = float(h["lat"]), float(h["lon"])
    if not (34 <= lat <= 72 and -25 <= lon <= 45):
        raise HTTPException(400, f"'{q}' is outside Europe")
    d = 0.02
    query = (f'[out:json][timeout:60];nwr["amenity"~"^(restaurant|cafe|fast_food)$"]'
             f'({lat - d},{lon - d * 1.4},{lat + d},{lon + d * 1.4});out tags;')
    try:
        data = await asyncio.to_thread(overpass, query, 3)
    except Exception as e:
        raise HTTPException(503, f"OpenStreetMap is busy, try again ({e})")
    els = data.get("elements", [])
    veg = sum(1 for el in els if el.get("tags", {}).get("diet:vegetarian") in ("yes", "only")
              or el.get("tags", {}).get("diet:vegan") in ("yes", "only"))
    addr = h.get("address", {})
    return {"id": None, "name": h.get("name") or q, "country": addr.get("country"),
            "country_code": (addr.get("country_code") or "").upper(), "lat": lat, "lon": lon,
            "in_catalog": False, "total": len(els), "veg_tagged": veg,
            "sample": [el["tags"].get("name") for el in els if el.get("tags", {}).get("name")][:8]}


@app.get("/api/stats/city/{city_id}/buildings")
async def city_buildings(city_id: str, user: str = Depends(current_user)):
    c = city_by_id(city_id)
    if not c:
        raise HTTPException(404)
    try:
        return await asyncio.to_thread(get_buildings, city_dict(c))
    except Exception as e:
        raise HTTPException(503, f"Building data unavailable: {e}")
