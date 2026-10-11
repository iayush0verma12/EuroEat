"""Cached access to menus and reviews for a restaurant."""
import json
import re
from urllib.parse import quote_plus

from app.cities import COUNTRIES, city_by_id, city_dict
from app.db import dumps, get_db
from app.knowledge.menus import estimated_menu
from app.knowledge.reviews import generate_reviews
from app.scrape.menu import scrape_menu

MEAT_WORDS = re.compile(
    r"\b(pollo|chicken|poulet|pollo|hähnchen|huhn|frango|kip|jamón|jamon|pernil|ham|jambon|prosciutto|"
    r"schinken|presunto|ham|beef|ternera|vedella|boeuf|bœuf|manzo|rind|vaca|rundvlees|pork|cerdo|porc|"
    r"maiale|schwein|porco|varken|lamb|cordero|xai|agneau|agnello|lamm|borrego|bacon|bacó|chorizo|"
    r"salami|sausage|salchicha|botifarra|saucisse|salsiccia|wurst|chouriço|duck|pato|canard|anatra|"
    r"ente|fish|pescado|peix|poisson|pesce|fisch|peixe|vis|tuna|atún|tonyina|thon|tonno|salmon|salmón|"
    r"saumon|salmone|lachs|salmão|cod|bacalao|bacallà|bacalhau|morue|shrimp|prawn|gamba|gambes|"
    r"crevette|gambero|garnele|camarão|octopus|pulpo|pop|poulpe|polpo|squid|calamar|calamars|seafood|"
    r"marisco|marisc|fruits de mer|frutti di mare|meeresfrüchte|anchovy|anchoa|anxova|anchois|acciuga|"
    r"steak|burger de ternera|carne|meat|viande|fleisch|vlees|veal|ternasco|conejo|rabbit|lapin|"
    r"secreto|iberico|ibérico|carbonara|bolognese|kebab|döner|gyros|souvlaki)\b", re.I)
VEG_WORDS = re.compile(r"\b(veg|vegan|vegano|vegana|vegà|végétarien|vegetarian|vegetariano|vegetarià|"
                       r"vegetarisch|tofu|seitan|tempeh|heura|falafel|verdur|légume|verdure|gemüse|legumes|"
                       r"queso|formatge|fromage|formaggio|käse|cheese|setas|bolets|champignon|funghi|pilz)", re.I)
BREAKFAST_WORDS = re.compile(r"\b(breakfast|desayuno|esmorzar|petit[- ]d[ée]jeuner|colazione|frühstück|"
                             r"pequeno[- ]almoço|ontbijt|croissant|cornetto|toast|tostada|torrada|coffee|"
                             r"café|caffè|kaffee|cappuccino|pastry|bollería|granola|porridge|pancake|"
                             r"brunch|eggs|huevos|ous)\b", re.I)


def classify_veg(name: str, veg_restaurant: bool) -> bool:
    if MEAT_WORDS.search(name):
        return False
    if veg_restaurant:
        return True
    return bool(VEG_WORDS.search(name))


def guess_meal(name: str) -> str:
    return "breakfast" if BREAKFAST_WORDS.search(name) else "any"


def links_for(rest: dict, menu_page: str | None = None) -> dict:
    osm_type, osm_id = rest["id"].split("/")
    q = quote_plus(f"{rest['name']} {rest.get('address') or ''} {rest['city_id']}")
    return {
        "website": rest.get("website"),
        "menu": menu_page or rest.get("menu_url") or rest.get("website"),
        "osm": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        "google_maps": f"https://www.google.com/maps/search/?api=1&query={q}",
    }


def city_ctx(city_id: str) -> dict:
    return city_dict(city_by_id(city_id))


async def get_menu(rest: dict, scrape=True) -> dict:
    """Return cached menu or scrape/estimate one. Shape:
    {source, source_url, menu_page, lang, items:[{name, name_en?, price, currency, vegetarian, meal}], note}"""
    with get_db() as db:
        row = db.execute("SELECT * FROM menus WHERE restaurant_id=?", (rest["id"],)).fetchone()
    if row:
        m = json.loads(row["raw_text"] or "{}")
        m.update({"source": row["source"], "source_url": row["source_url"], "lang": row["lang"],
                  "items": json.loads(row["items_json"])})
        return m
    city = city_ctx(rest["city_id"])
    veg_rest = rest.get("diet_vegetarian") == "only" or rest.get("diet_vegan") == "only"
    scraped = {"items": [], "menu_page": None, "pdf": None, "method": None, "source_url": None}
    if scrape and (rest.get("website") or rest.get("menu_url")):
        try:
            scraped = await scrape_menu(rest, city["currency"])
        except Exception:
            pass
    if len(scraped["items"]) >= 4:
        items = [{**it, "vegetarian": classify_veg(it["name"], veg_rest), "meal": guess_meal(it["name"])}
                 for it in scraped["items"]]
        menu = {"source": "scraped", "source_url": scraped["source_url"], "menu_page": scraped["menu_page"],
                "pdf": scraped["pdf"], "method": scraped["method"], "lang": city["lang"], "items": items,
                "note": f"Read from the restaurant's own site via {scraped['method']}"}
    else:
        items = estimated_menu(rest, city["lang"], city["currency"])
        reason = ("no website listed" if not (rest.get("website") or rest.get("menu_url"))
                  else "website unreachable or no machine-readable prices")
        lang = city["lang"] if city["lang"] in ("es", "fr", "it", "de", "pt", "nl") else "en"
        menu = {"source": "estimated", "source_url": rest.get("website"), "menu_page": scraped.get("menu_page"),
                "pdf": scraped.get("pdf"), "method": None, "lang": lang, "items": items,
                "note": f"Estimated from regional dishes ({reason}); prices are indicative"}
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO menus (restaurant_id, source, source_url, lang, items_json, raw_text) "
            "VALUES (?,?,?,?,?,?)",
            (rest["id"], menu["source"], menu["source_url"], menu["lang"], dumps(menu["items"]),
             dumps({k: menu.get(k) for k in ("menu_page", "pdf", "method", "note")})))
    return menu


def save_menu_items(rest_id: str, items: list[dict]):
    with get_db() as db:
        db.execute("UPDATE menus SET items_json=? WHERE restaurant_id=?", (dumps(items), rest_id))


def get_reviews(rest: dict) -> list[dict]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM reviews WHERE restaurant_id=? ORDER BY id", (rest["id"],)).fetchall()
        if rows:
            return [dict(r) for r in rows]
        lang = COUNTRIES[rest["country_code"]]["lang"]
        revs = generate_reviews(rest, lang)
        db.executemany(
            "INSERT INTO reviews (restaurant_id, author, rating, lang, text, text_en, source, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [(rest["id"], r["author"], r["rating"], r["lang"], r["text"], r["text_en"], r["source"],
              r["created_at"]) for r in revs])
        avg = round(sum(r["rating"] for r in revs) / len(revs), 1)
        db.execute("UPDATE restaurants SET rating=? WHERE id=?", (avg, rest["id"]))
        rows = db.execute("SELECT * FROM reviews WHERE restaurant_id=? ORDER BY id", (rest["id"],)).fetchall()
        return [dict(r) for r in rows]
