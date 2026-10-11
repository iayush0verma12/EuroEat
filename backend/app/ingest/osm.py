"""Ingest real restaurant data for European cities from OpenStreetMap (Overpass API).

Usage:
    python -m app.ingest.osm                 # all cities in the catalog
    python -m app.ingest.osm barcelona paris # selected cities

OSM data is © OpenStreetMap contributors, available under the ODbL.
"""
import hashlib
import json
import sys
import time

import httpx

from app.cities import CITIES, city_by_id, city_dict
from app.db import dumps, get_db, init_db

# main instance first and most often; mirrors are a last resort (often overloaded)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "EuroEatAgent/1.0 (restaurant recommender demo)"}


def overpass(query: str, retries: int = 6) -> dict:
    last = None
    for attempt in range(retries):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            r = httpx.post(url, data={"data": query}, headers=HEADERS, timeout=180)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                return r.json()
            last = f"{r.status_code}: {r.text[:200]}"
        except Exception as e:  # network hiccup / timeout
            last = str(e)
        time.sleep(4 + attempt * 4)
    raise RuntimeError(f"Overpass failed: {last}")


def _price_level(tags: dict, amenity: str, oid: str) -> int:
    if amenity == "fast_food":
        return 1
    if amenity == "cafe":
        return 1 if int(hashlib.md5(oid.encode()).hexdigest(), 16) % 3 else 2
    if "michelin" in json.dumps(tags).lower() or tags.get("stars"):
        return 4
    # deterministic estimate (OSM rarely has price info)
    return 2 + int(hashlib.md5(oid.encode()).hexdigest(), 16) % 2


def _address(tags: dict) -> str:
    parts = [
        " ".join(p for p in [tags.get("addr:street"), tags.get("addr:housenumber")] if p),
        tags.get("addr:postcode"),
        tags.get("addr:city"),
    ]
    return ", ".join(p for p in parts if p)


def _norm_url(u):
    if not u:
        return None
    u = u.strip().split(";")[0]
    if not u.startswith("http"):
        u = "https://" + u
    return u


def _fetch_bbox(s, w, n, e, depth=0) -> list[dict]:
    q = f"""[out:json][timeout:170];
    nwr["amenity"~"^(restaurant|cafe|fast_food)$"]["name"]({s},{w},{n},{e});
    out center tags;"""
    try:
        return overpass(q, retries=3 if depth < 2 else 6).get("elements", [])
    except RuntimeError:
        if depth >= 2:
            raise
        # dense city centre: split the box into 4 tiles and try again
        mlat, mlon = (s + n) / 2, (w + e) / 2
        out = []
        for box in ((s, w, mlat, mlon), (s, mlon, mlat, e), (mlat, w, n, mlon), (mlat, mlon, n, e)):
            out += _fetch_bbox(*box, depth=depth + 1)
            time.sleep(2)
        return out


def ingest_city(city_id: str) -> int:
    c = city_dict(city_by_id(city_id))
    s, w, n, e = c["bbox"]
    rows = []
    for el in _fetch_bbox(s, w, n, e):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        oid = f"{el['type']}/{el['id']}"
        amenity = tags.get("amenity")
        cuisine = (tags.get("cuisine") or "").replace("_", " ")
        veg = tags.get("diet:vegetarian")
        vegan = tags.get("diet:vegan")
        if not veg and any(k in cuisine for k in ("vegetarian", "vegan")):
            veg = "only" if "vegetarian" in cuisine else "yes"
        breakfast = 1 if (
            tags.get("breakfast") == "yes"
            or amenity == "cafe"
            or "breakfast" in cuisine
            or "brunch" in cuisine
            or "bakery" in cuisine
        ) else 0
        rows.append((
            oid, city_id, c["country_code"], tags.get("name"), amenity, cuisine or None,
            lat, lon, _address(tags) or None,
            _norm_url(tags.get("website") or tags.get("contact:website")),
            _norm_url(tags.get("website:menu") or tags.get("menu:url")),
            tags.get("phone") or tags.get("contact:phone"),
            tags.get("opening_hours"), veg, vegan, breakfast,
            tags.get("takeaway"), tags.get("delivery"),
            _price_level(tags, amenity, oid), dumps(tags),
        ))
    with get_db() as db:
        db.executemany(
            """INSERT INTO restaurants (id, city_id, country_code, name, amenity, cuisine, lat, lon,
                 address, website, menu_url, phone, opening_hours, diet_vegetarian, diet_vegan,
                 breakfast, takeaway, delivery, price_level, tags_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, cuisine=excluded.cuisine, website=excluded.website,
                 menu_url=excluded.menu_url, opening_hours=excluded.opening_hours,
                 diet_vegetarian=excluded.diet_vegetarian, diet_vegan=excluded.diet_vegan,
                 tags_json=excluded.tags_json""",
            rows,
        )
    return len(rows)


def main(ids):
    init_db()
    ids = ids or [c[0] for c in CITIES]
    total = 0
    for cid in ids:
        try:
            n = ingest_city(cid)
            total += n
            print(f"[osm] {cid:12s} {n:6d} places", flush=True)
        except Exception as e:
            print(f"[osm] {cid:12s} FAILED: {e}", flush=True)
        time.sleep(2)
    print(f"[osm] done, {total} places ingested", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
