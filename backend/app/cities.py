"""Catalog of European countries / cities the agent knows about.

Each city has a centre point and a half-size (degrees) for the bounding box used
when ingesting restaurants from OpenStreetMap, plus the local language used for
menus and reviews (drives the translation step of the agent).
"""

COUNTRIES = {
    "ES": {"name": "Spain", "lang": "es", "currency": "EUR"},
    "FR": {"name": "France", "lang": "fr", "currency": "EUR"},
    "IT": {"name": "Italy", "lang": "it", "currency": "EUR"},
    "DE": {"name": "Germany", "lang": "de", "currency": "EUR"},
    "PT": {"name": "Portugal", "lang": "pt", "currency": "EUR"},
    "NL": {"name": "Netherlands", "lang": "nl", "currency": "EUR"},
    "GB": {"name": "United Kingdom", "lang": "en", "currency": "GBP"},
    "AT": {"name": "Austria", "lang": "de", "currency": "EUR"},
    "CZ": {"name": "Czech Republic", "lang": "cs", "currency": "CZK"},
    "GR": {"name": "Greece", "lang": "el", "currency": "EUR"},
    "BE": {"name": "Belgium", "lang": "fr", "currency": "EUR"},
    "CH": {"name": "Switzerland", "lang": "de", "currency": "CHF"},
    "IE": {"name": "Ireland", "lang": "en", "currency": "EUR"},
    "DK": {"name": "Denmark", "lang": "da", "currency": "DKK"},
    "SE": {"name": "Sweden", "lang": "sv", "currency": "SEK"},
    "PL": {"name": "Poland", "lang": "pl", "currency": "PLN"},
    "HU": {"name": "Hungary", "lang": "hu", "currency": "HUF"},
    "NO": {"name": "Norway", "lang": "no", "currency": "NOK"},
}

# id, name, country, lat, lon, half_size_deg
CITIES = [
    ("barcelona", "Barcelona", "ES", 41.3888, 2.1640, 0.035),
    ("madrid", "Madrid", "ES", 40.4168, -3.7038, 0.035),
    ("valencia", "Valencia", "ES", 39.4699, -0.3763, 0.025),
    ("seville", "Seville", "ES", 37.3891, -5.9845, 0.025),
    ("paris", "Paris", "FR", 48.8566, 2.3522, 0.035),
    ("lyon", "Lyon", "FR", 45.7640, 4.8357, 0.025),
    ("nice", "Nice", "FR", 43.7102, 7.2620, 0.02),
    ("rome", "Rome", "IT", 41.9028, 12.4964, 0.035),
    ("milan", "Milan", "IT", 45.4642, 9.1900, 0.03),
    ("florence", "Florence", "IT", 43.7696, 11.2558, 0.02),
    ("venice", "Venice", "IT", 45.4371, 12.3326, 0.015),
    ("berlin", "Berlin", "DE", 52.5200, 13.4050, 0.035),
    ("munich", "Munich", "DE", 48.1351, 11.5820, 0.03),
    ("hamburg", "Hamburg", "DE", 53.5511, 9.9937, 0.025),
    ("lisbon", "Lisbon", "PT", 38.7223, -9.1393, 0.03),
    ("porto", "Porto", "PT", 41.1579, -8.6291, 0.02),
    ("amsterdam", "Amsterdam", "NL", 52.3676, 4.9041, 0.03),
    ("rotterdam", "Rotterdam", "NL", 51.9244, 4.4777, 0.02),
    ("london", "London", "GB", 51.5072, -0.1276, 0.035),
    ("edinburgh", "Edinburgh", "GB", 55.9533, -3.1883, 0.02),
    ("vienna", "Vienna", "AT", 48.2082, 16.3738, 0.03),
    ("prague", "Prague", "CZ", 50.0755, 14.4378, 0.03),
    ("athens", "Athens", "GR", 37.9838, 23.7275, 0.03),
    ("brussels", "Brussels", "BE", 50.8503, 4.3517, 0.025),
    ("zurich", "Zurich", "CH", 47.3769, 8.5417, 0.02),
    ("dublin", "Dublin", "IE", 53.3498, -6.2603, 0.025),
    ("copenhagen", "Copenhagen", "DK", 55.6761, 12.5683, 0.025),
    ("stockholm", "Stockholm", "SE", 59.3293, 18.0686, 0.025),
    ("warsaw", "Warsaw", "PL", 52.2297, 21.0122, 0.03),
    ("krakow", "Krakow", "PL", 50.0647, 19.9450, 0.02),
    ("budapest", "Budapest", "HU", 47.4979, 19.0402, 0.03),
    ("oslo", "Oslo", "NO", 59.9139, 10.7522, 0.02),
]


def city_by_id(city_id: str):
    for c in CITIES:
        if c[0] == city_id:
            return c
    return None


def city_dict(c):
    cid, name, cc, lat, lon, half = c
    return {
        "id": cid,
        "name": name,
        "country_code": cc,
        "country": COUNTRIES[cc]["name"],
        "lat": lat,
        "lon": lon,
        "lang": COUNTRIES[cc]["lang"],
        "currency": COUNTRIES[cc]["currency"],
        "bbox": [lat - half, lon - half * 1.4, lat + half, lon + half * 1.4],
    }
