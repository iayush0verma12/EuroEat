"""Fetch building footprints around a city centre for the three.js cityscape."""
import json

from app.db import get_db
from app.ingest.osm import overpass


def _height(tags: dict) -> float:
    h = tags.get("height") or ""
    try:
        return float(h.replace("m", "").strip())
    except ValueError:
        pass
    try:
        return float(tags.get("building:levels")) * 3.2
    except (TypeError, ValueError):
        return 0


def get_buildings(city: dict, radius_deg: float = 0.0065) -> dict:
    with get_db() as db:
        row = db.execute("SELECT geojson FROM city_buildings WHERE city_id=?", (city["id"],)).fetchone()
    if row:
        return json.loads(row["geojson"])
    lat, lon = city["lat"], city["lon"]
    s, n = lat - radius_deg, lat + radius_deg
    w, e = lon - radius_deg * 1.4, lon + radius_deg * 1.4
    data = overpass(f"""[out:json][timeout:120];
        way["building"]({s},{w},{n},{e});
        out geom tags;""", retries=4)
    feats = []
    for el in data.get("elements", []):
        geom = el.get("geometry")
        if not geom or len(geom) < 4:
            continue
        tags = el.get("tags", {})
        feats.append({"h": _height(tags), "c": [[round(p["lon"], 6), round(p["lat"], 6)] for p in geom]})
    out = {"center": [lon, lat], "bbox": [w, s, e, n], "buildings": feats}
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO city_buildings (city_id, geojson) VALUES (?,?)",
                   (city["id"], json.dumps(out)))
    return out
