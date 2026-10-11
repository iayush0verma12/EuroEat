"""Demo coupon engine: evaluates every coupon against the cart and picks the best."""
import datetime as dt
import hashlib

COUPONS = [
    {"code": "WELCOME10", "title": "10% off your first EuroEat order", "kind": "any",
     "percent": 10, "min_subtotal": 0, "max_discount": 15},
    {"code": "VEGGIE15", "title": "15% off at vegetarian/vegan-tagged places", "kind": "any",
     "percent": 15, "min_subtotal": 15, "max_discount": 20, "requires_veg_tag": True},
    {"code": "DINEIN20", "title": "20% off dine-in lunch on weekdays", "kind": "dine_in",
     "percent": 20, "min_subtotal": 20, "max_discount": 25, "meal": "lunch", "weekday_only": True},
    {"code": "EARLYBIRD5", "title": "5.00 off breakfast orders over 15.00", "kind": "any",
     "flat": 5, "min_subtotal": 15, "meal": "breakfast"},
    {"code": "FREEDEL", "title": "Free delivery (3.50) on online orders over 25.00", "kind": "order_online",
     "flat": 3.5, "min_subtotal": 25},
    {"code": "PARTNER25", "title": "25% off at EuroEat partner restaurants", "kind": "any",
     "percent": 25, "min_subtotal": 30, "max_discount": 30, "partner_only": True},
]


def is_partner(restaurant_id: str) -> bool:
    return int(hashlib.md5(restaurant_id.encode()).hexdigest(), 16) % 4 == 0


def evaluate(restaurant: dict, kind: str, meal: str, subtotal: float, when: dt.date | None = None):
    when = when or dt.date.today()
    veg = restaurant.get("diet_vegetarian") in ("yes", "only") or restaurant.get("diet_vegan") in ("yes", "only")
    partner = is_partner(restaurant["id"])
    out = []
    for c in COUPONS:
        reason = None
        if c["kind"] != "any" and c["kind"] != kind:
            reason = f"only for {c['kind'].replace('_', ' ')}"
        elif subtotal < c["min_subtotal"]:
            reason = f"minimum {c['min_subtotal']:.2f}"
        elif c.get("requires_veg_tag") and not veg:
            reason = "restaurant not tagged vegetarian"
        elif c.get("meal") and c["meal"] != meal:
            reason = f"{c['meal']} only"
        elif c.get("weekday_only") and when.weekday() >= 5:
            reason = "weekdays only"
        elif c.get("partner_only") and not partner:
            reason = "not a partner restaurant"
        if "percent" in c:
            disc = min(subtotal * c["percent"] / 100, c.get("max_discount", 1e9))
        else:
            disc = min(c["flat"], subtotal)
        out.append({"code": c["code"], "title": c["title"], "applicable": reason is None,
                    "reason": reason, "discount": round(disc, 2) if reason is None else 0})
    out.sort(key=lambda x: (-x["applicable"], -x["discount"]))
    best = out[0] if out and out[0]["applicable"] else None
    return {"best": best, "all": out, "partner": partner}
