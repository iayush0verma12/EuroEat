"""Regional dish knowledge used when a restaurant's real menu can't be scraped.

Dishes are stored in the local language (with an English gloss used only as an
offline fallback when the LLM translator is unavailable). Generated menus are
always flagged with source="estimated" so the UI never presents them as scraped.
"""
import hashlib
import random

# (local name, english gloss, vegetarian, meal, base price in EUR)
B, L, D, A = "breakfast", "lunch", "dinner", "any"

REGIONAL = {
    "es": [
        ("Pan con tomate", "Bread with tomato", True, B, 3.5),
        ("Tostada de aguacate", "Avocado toast", True, B, 6.5),
        ("Churros con chocolate", "Churros with hot chocolate", True, B, 5.0),
        ("Café con leche y croissant", "Latte and croissant", True, B, 4.2),
        ("Tortilla de patatas", "Spanish potato omelette", True, A, 7.0),
        ("Bocadillo de jamón ibérico", "Iberian ham sandwich", False, B, 7.5),
        ("Patatas bravas", "Fried potatoes with spicy sauce", True, A, 6.0),
        ("Pimientos de Padrón", "Blistered Padrón peppers", True, A, 6.5),
        ("Escalivada con pan de coca", "Roasted vegetables on flatbread", True, A, 9.0),
        ("Gazpacho andaluz", "Cold Andalusian tomato soup", True, L, 6.5),
        ("Espinacas a la catalana", "Catalan spinach with raisins and pine nuts", True, A, 8.0),
        ("Croquetas de setas", "Mushroom croquettes", True, A, 8.5),
        ("Croquetas de jamón", "Ham croquettes", False, A, 8.5),
        ("Paella de verduras", "Vegetable paella", True, L, 16.0),
        ("Paella de marisco", "Seafood paella", False, L, 19.5),
        ("Arroz negro", "Black rice with squid ink", False, D, 18.0),
        ("Fideuá", "Seafood noodle paella", False, D, 17.0),
        ("Pulpo a la gallega", "Galician-style octopus", False, D, 18.5),
        ("Calçots con salsa romesco", "Grilled spring onions with romesco", True, D, 12.0),
        ("Berenjenas con miel", "Fried aubergine with honey", True, D, 9.5),
        ("Ensalada de queso de cabra", "Goat cheese salad", True, L, 11.0),
        ("Menú del día vegetariano", "Vegetarian set lunch menu", True, L, 14.5),
        ("Menú del día", "Set lunch menu", False, L, 14.5),
        ("Crema catalana", "Catalan crème brûlée", True, A, 5.5),
        ("Secreto ibérico", "Iberian pork cut", False, D, 19.0),
    ],
    "fr": [
        ("Croissant au beurre", "Butter croissant", True, B, 2.2),
        ("Tartine beurre-confiture", "Bread with butter and jam", True, B, 4.0),
        ("Omelette aux fines herbes", "Herb omelette", True, B, 9.0),
        ("Croque-madame", "Ham and cheese toastie with egg", False, L, 12.0),
        ("Quiche aux poireaux", "Leek quiche", True, L, 11.0),
        ("Soupe à l'oignon gratinée", "French onion soup", True, A, 10.5),
        ("Ratatouille provençale", "Provençal vegetable stew", True, A, 15.0),
        ("Salade de chèvre chaud", "Warm goat cheese salad", True, L, 14.0),
        ("Galette complète", "Buckwheat crêpe with ham, egg and cheese", False, L, 12.5),
        ("Galette aux champignons", "Buckwheat crêpe with mushrooms", True, L, 12.0),
        ("Boeuf bourguignon", "Beef braised in red wine", False, D, 24.0),
        ("Confit de canard", "Duck confit", False, D, 25.0),
        ("Risotto aux cèpes", "Porcini mushroom risotto", True, D, 21.0),
        ("Gratin dauphinois", "Potato gratin", True, D, 9.0),
        ("Tarte Tatin", "Caramelised upside-down apple tart", True, A, 8.5),
        ("Crème brûlée", "Crème brûlée", True, A, 8.0),
    ],
    "it": [
        ("Cornetto e cappuccino", "Croissant and cappuccino", True, B, 3.5),
        ("Brioche alla crema", "Cream-filled brioche", True, B, 2.5),
        ("Bruschetta al pomodoro", "Tomato bruschetta", True, A, 7.0),
        ("Caprese di bufala", "Buffalo mozzarella and tomato salad", True, L, 11.0),
        ("Pizza Margherita", "Margherita pizza", True, A, 9.5),
        ("Pizza alle verdure grigliate", "Grilled vegetable pizza", True, A, 12.0),
        ("Pizza diavola", "Spicy salami pizza", False, A, 12.5),
        ("Spaghetti cacio e pepe", "Spaghetti with pecorino and pepper", True, A, 13.0),
        ("Penne all'arrabbiata", "Penne in spicy tomato sauce", True, L, 11.0),
        ("Spaghetti alla carbonara", "Spaghetti carbonara", False, A, 14.0),
        ("Risotto ai funghi porcini", "Porcini risotto", True, D, 17.0),
        ("Melanzane alla parmigiana", "Aubergine parmigiana", True, D, 14.0),
        ("Gnocchi al pesto", "Gnocchi with pesto", True, A, 13.5),
        ("Lasagne alla bolognese", "Beef lasagne", False, D, 15.0),
        ("Ossobuco alla milanese", "Braised veal shank", False, D, 26.0),
        ("Tiramisù", "Tiramisu", True, A, 7.0),
    ],
    "de": [
        ("Brezel mit Butter", "Pretzel with butter", True, B, 3.0),
        ("Bircher Müsli", "Bircher muesli", True, B, 7.5),
        ("Rührei mit Schnittlauch", "Scrambled eggs with chives", True, B, 8.5),
        ("Weißwurstfrühstück", "White sausage breakfast", False, B, 12.0),
        ("Käsespätzle", "Cheese spätzle noodles", True, A, 14.0),
        ("Kartoffelsuppe", "Potato soup", True, L, 7.5),
        ("Gemüse-Maultaschen", "Vegetable-filled pasta pockets", True, L, 13.0),
        ("Flammkuchen mit Ziegenkäse", "Tarte flambée with goat cheese", True, D, 13.5),
        ("Wiener Schnitzel", "Breaded veal cutlet", False, D, 22.0),
        ("Currywurst mit Pommes", "Curry sausage with fries", False, L, 9.5),
        ("Schweinshaxe", "Roast pork knuckle", False, D, 21.0),
        ("Rote-Bete-Salat mit Feta", "Beetroot salad with feta", True, L, 11.5),
        ("Pilzrahmschnitzel vom Sellerie", "Celeriac schnitzel with mushroom sauce", True, D, 17.0),
        ("Apfelstrudel", "Apple strudel", True, A, 7.0),
    ],
    "pt": [
        ("Pastel de nata", "Custard tart", True, B, 1.5),
        ("Torrada com manteiga e galão", "Toast with butter and milky coffee", True, B, 3.5),
        ("Caldo verde", "Kale and potato soup", False, L, 4.5),
        ("Sopa de legumes", "Vegetable soup", True, L, 4.0),
        ("Bacalhau à Brás", "Shredded salt cod with eggs and potato", False, A, 15.0),
        ("Francesinha", "Meat-filled sandwich in beer sauce", False, L, 13.0),
        ("Francesinha vegetariana", "Vegetarian francesinha", True, L, 13.0),
        ("Arroz de cogumelos", "Mushroom rice", True, D, 14.0),
        ("Polvo à lagareiro", "Roasted octopus with olive oil", False, D, 22.0),
        ("Salada de grão-de-bico", "Chickpea salad", True, L, 9.5),
        ("Queijo da Serra no forno", "Baked Serra cheese", True, D, 14.5),
        ("Arroz doce", "Rice pudding", True, A, 5.0),
    ],
    "nl": [
        ("Uitsmijter met kaas", "Fried eggs on bread with cheese", True, B, 9.5),
        ("Poffertjes", "Mini pancakes", True, B, 7.0),
        ("Pannenkoek met appel", "Apple pancake", True, L, 11.0),
        ("Erwtensoep", "Split pea soup", False, L, 8.0),
        ("Tosti kaas", "Cheese toastie", True, L, 6.5),
        ("Kroketten op brood", "Croquettes on bread", False, L, 9.0),
        ("Bitterballen", "Fried meat balls", False, A, 8.0),
        ("Groentenstamppot", "Mashed potato and vegetable stew", True, D, 15.5),
        ("Hutspot met rookworst", "Mash with smoked sausage", False, D, 17.0),
        ("Kaasfondue", "Cheese fondue", True, D, 22.0),
        ("Appeltaart met slagroom", "Apple pie with whipped cream", True, A, 5.5),
    ],
    "en": [
        ("Full English breakfast", "Full English breakfast", False, B, 13.0),
        ("Vegetarian full breakfast", "Vegetarian full breakfast", True, B, 12.0),
        ("Avocado toast with poached eggs", "Avocado toast with poached eggs", True, B, 11.0),
        ("Porridge with berries", "Porridge with berries", True, B, 7.0),
        ("Tomato soup with sourdough", "Tomato soup with sourdough", True, L, 7.5),
        ("Halloumi wrap", "Halloumi wrap", True, L, 10.0),
        ("Fish and chips", "Fish and chips", False, A, 16.0),
        ("Mushroom and ale pie", "Mushroom and ale pie", True, D, 16.5),
        ("Steak and ale pie", "Steak and ale pie", False, D, 18.0),
        ("Cauliflower cheese", "Cauliflower cheese", True, D, 12.0),
        ("Sunday roast", "Sunday roast", False, D, 22.0),
        ("Nut roast with all the trimmings", "Nut roast with all the trimmings", True, D, 19.0),
        ("Sticky toffee pudding", "Sticky toffee pudding", True, A, 7.5),
    ],
}

CUISINE = {
    "indian": [
        ("Paneer tikka masala", "Paneer tikka masala", True, A, 14.0),
        ("Chana masala", "Chickpea curry", True, A, 12.0),
        ("Dal makhani", "Creamy black lentils", True, A, 11.5),
        ("Vegetable biryani", "Vegetable biryani", True, A, 13.5),
        ("Masala dosa", "Masala dosa", True, B, 10.0),
        ("Chicken tikka masala", "Chicken tikka masala", False, A, 15.0),
        ("Lamb rogan josh", "Lamb rogan josh", False, D, 17.0),
        ("Garlic naan", "Garlic naan", True, A, 3.5),
    ],
    "japanese": [
        ("Avocado maki", "Avocado roll", True, A, 7.0),
        ("Vegetable gyoza", "Vegetable dumplings", True, A, 7.5),
        ("Yasai ramen", "Vegetable ramen", True, A, 14.0),
        ("Tonkotsu ramen", "Pork broth ramen", False, A, 15.0),
        ("Salmon nigiri", "Salmon nigiri", False, A, 9.0),
        ("Agedashi tofu", "Fried tofu in broth", True, A, 8.0),
    ],
    "asian": [
        ("Tofu pad thai", "Tofu pad thai", True, A, 13.0),
        ("Green curry with vegetables", "Green curry with vegetables", True, A, 14.0),
        ("Bánh mì chay", "Vegetarian Vietnamese baguette", True, L, 9.0),
        ("Pho bo", "Beef noodle soup", False, A, 13.5),
        ("Vegetable spring rolls", "Vegetable spring rolls", True, A, 7.0),
    ],
    "mexican": [
        ("Tacos de hongos", "Mushroom tacos", True, A, 11.0),
        ("Quesadilla de queso", "Cheese quesadilla", True, A, 9.0),
        ("Guacamole con totopos", "Guacamole with tortilla chips", True, A, 8.0),
        ("Tacos al pastor", "Marinated pork tacos", False, A, 12.0),
        ("Burrito de frijoles", "Bean burrito", True, L, 11.5),
    ],
    "vegetarian": [
        ("Buddha bowl", "Buddha bowl", True, L, 13.5),
        ("Beyond burger", "Plant-based burger", True, A, 14.0),
        ("Falafel plate with hummus", "Falafel plate with hummus", True, A, 12.5),
        ("Açaí bowl", "Açaí bowl", True, B, 9.5),
        ("Vegan pancakes", "Vegan pancakes", True, B, 10.0),
        ("Seitan shawarma", "Seitan shawarma", True, D, 15.0),
        ("Lentil dahl with rice", "Lentil dahl with rice", True, A, 12.0),
    ],
    "burger": [
        ("Classic cheeseburger", "Classic cheeseburger", False, A, 12.0),
        ("Veggie burger", "Veggie burger", True, A, 12.0),
        ("Sweet potato fries", "Sweet potato fries", True, A, 5.0),
    ],
    "cafe": [
        ("Cappuccino", "Cappuccino", True, B, 3.2),
        ("Granola with yoghurt", "Granola with yoghurt", True, B, 7.5),
        ("Banana bread", "Banana bread", True, B, 4.0),
        ("Eggs Benedict", "Eggs Benedict", False, B, 12.0),
        ("Eggs Florentine", "Eggs Florentine (spinach)", True, B, 12.0),
        ("Grilled vegetable sandwich", "Grilled vegetable sandwich", True, L, 8.5),
    ],
}

CUISINE_ALIASES = {
    "pizza": "it", "italian": "it", "spanish": "es", "tapas": "es", "catalan": "es",
    "french": "fr", "german": "de", "portuguese": "pt", "dutch": "nl", "british": "en",
    "vegan": "vegetarian", "healthy": "vegetarian", "organic": "vegetarian",
    "sushi": "japanese", "ramen": "japanese", "thai": "asian", "vietnamese": "asian",
    "chinese": "asian", "korean": "asian", "nepalese": "indian", "pakistani": "indian",
    "coffee shop": "cafe", "breakfast": "cafe", "brunch": "cafe", "bakery": "cafe",
    "american": "burger",
}

# multiply EUR base prices into local currency / price level
FX = {"EUR": 1.0, "GBP": 0.86, "CZK": 25.0, "CHF": 1.5, "DKK": 8.5, "SEK": 12.0,
      "PLN": 4.3, "HUF": 395.0, "NOK": 13.0}
COUNTRY_COST = {"CH": 1.6, "NO": 1.45, "DK": 1.3, "GB": 1.15, "IE": 1.15, "SE": 1.15,
                "CZ": 0.7, "PL": 0.65, "HU": 0.65, "GR": 0.85, "PT": 0.85}
PRICE_LEVEL = {1: 0.75, 2: 1.0, 3: 1.3, 4: 2.0}


def _pools(cuisine: str | None, lang: str, amenity: str | None):
    pools = []
    for c in (cuisine or "").split(";"):
        c = c.strip()
        key = CUISINE_ALIASES.get(c, c)
        if key in CUISINE:
            pools.append(CUISINE[key])
        elif key in REGIONAL:
            pools.append(REGIONAL[key])
    if amenity == "cafe":
        pools.append(CUISINE["cafe"])
    pools.append(REGIONAL.get(lang, REGIONAL["en"]))
    return pools


def estimated_menu(rest: dict, lang: str, currency: str) -> list[dict]:
    seed = int(hashlib.md5(rest["id"].encode()).hexdigest(), 16)
    rnd = random.Random(seed)
    items, seen = [], set()
    for pool in _pools(rest.get("cuisine"), lang, rest.get("amenity")):
        k = min(len(pool), rnd.randint(6, 10))
        for dish in rnd.sample(pool, k):
            if dish[0] in seen:
                continue
            seen.add(dish[0])
            items.append(dish)
    factor = (FX.get(currency, 1.0) * COUNTRY_COST.get(rest.get("country_code"), 1.0)
              * PRICE_LEVEL.get(rest.get("price_level") or 2, 1.0))
    out = []
    for local, en, veg, meal, base in items[:18]:
        price = base * factor * rnd.uniform(0.9, 1.15)
        price = round(price) if FX.get(currency, 1) > 5 else round(price * 2) / 2
        out.append({"name": local, "gloss_en": en, "vegetarian": veg, "meal": meal,
                    "price": price, "currency": currency})
    return out
