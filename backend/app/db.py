import json
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "EUROEAT_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "euroeat.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS restaurants (
    id            TEXT PRIMARY KEY,          -- osm type/id, e.g. node/123
    city_id       TEXT NOT NULL,
    country_code  TEXT NOT NULL,
    name          TEXT NOT NULL,
    amenity       TEXT,                      -- restaurant | cafe | fast_food
    cuisine       TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    address       TEXT,
    website       TEXT,
    menu_url      TEXT,
    phone         TEXT,
    opening_hours TEXT,
    diet_vegetarian TEXT,                    -- yes | only | no | NULL
    diet_vegan    TEXT,
    breakfast     INTEGER DEFAULT 0,
    takeaway      TEXT,
    delivery      TEXT,
    price_level   INTEGER,                   -- 1..4 (estimated)
    rating        REAL,                      -- aggregated from reviews
    tags_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_rest_city ON restaurants(city_id);
CREATE INDEX IF NOT EXISTS idx_rest_veg ON restaurants(city_id, diet_vegetarian);

CREATE TABLE IF NOT EXISTS menus (
    restaurant_id TEXT PRIMARY KEY,
    source        TEXT,                      -- scraped | estimated
    source_url    TEXT,
    lang          TEXT,
    items_json    TEXT,                      -- [{name, name_en, price, currency, vegetarian, course}]
    raw_text      TEXT,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT NOT NULL,
    author        TEXT,
    rating        INTEGER,
    lang          TEXT,
    text          TEXT,
    text_en       TEXT,
    source        TEXT,
    created_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_reviews_rest ON reviews(restaurant_id);

CREATE TABLE IF NOT EXISTS translations (
    src_lang      TEXT NOT NULL,
    src           TEXT NOT NULL,
    en            TEXT NOT NULL,
    PRIMARY KEY (src_lang, src)
);

CREATE TABLE IF NOT EXISTS city_buildings (
    city_id       TEXT PRIMARY KEY,
    geojson       TEXT,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    full_name     TEXT,
    email         TEXT,
    home_city     TEXT,
    diet          TEXT DEFAULT 'vegetarian',
    settings_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS orders (
    id            TEXT PRIMARY KEY,
    username      TEXT,
    restaurant_id TEXT,
    kind          TEXT,                      -- order_online | dine_in
    meal          TEXT,
    items_json    TEXT,
    party_size    INTEGER,
    slot          TEXT,
    coupon        TEXT,
    subtotal      REAL,
    discount      REAL,
    total         REAL,
    status        TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript(SCHEMA)


def row_to_restaurant(row) -> dict:
    d = dict(row)
    d.pop("tags_json", None)
    return d


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False)
