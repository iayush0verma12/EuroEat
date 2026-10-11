"""Review source for the agent.

There is no free, ToS-compliant public API for restaurant reviews (Google /
TripAdvisor / Yelp forbid scraping), so the default provider generates a
deterministic, multilingual *demo* review corpus per restaurant. Every review is
stored with source="demo-synthetic" and the UI labels it as such. The agent
pipeline (positive/negative split, translation, contextual search) is identical
for a real provider: plug one in by writing rows into the `reviews` table.
"""
import hashlib
import random

# aspect -> sentiment -> {lang: text}
ASPECTS = {
    "vegetarian": {
        "pos": {
            "en": "Great vegetarian options, the waiter explained which dishes were meat-free.",
            "es": "Muy buenas opciones vegetarianas, el camarero nos explicó qué platos no llevaban carne.",
            "fr": "Excellentes options végétariennes, le serveur nous a indiqué les plats sans viande.",
            "it": "Ottime opzioni vegetariane, il cameriere ci ha spiegato quali piatti erano senza carne.",
            "de": "Tolle vegetarische Auswahl, der Kellner hat erklärt, welche Gerichte fleischlos sind.",
        },
        "neg": {
            "en": "As a vegetarian I struggled - only one salad and the 'veggie' soup had ham stock.",
            "es": "Para vegetarianos casi nada, solo una ensalada y la sopa llevaba caldo de jamón.",
            "fr": "Peu de choix pour les végétariens, une seule salade et la soupe contenait du bouillon de jambon.",
            "it": "Poche scelte per vegetariani, solo un'insalata e la zuppa aveva brodo di prosciutto.",
            "de": "Für Vegetarier kaum etwas, nur ein Salat und die Suppe war mit Schinkenbrühe.",
        },
    },
    "vegan": {
        "pos": {
            "en": "Vegan dishes are clearly marked on the menu and they can veganise most plates.",
            "es": "Los platos veganos están bien marcados en la carta y adaptan casi todo.",
            "fr": "Les plats véganes sont bien indiqués et ils adaptent presque tout.",
            "it": "I piatti vegani sono ben indicati nel menù e adattano quasi tutto.",
            "de": "Vegane Gerichte sind klar gekennzeichnet und fast alles kann vegan zubereitet werden.",
        },
        "neg": {
            "en": "Nothing vegan except fries, cheese is in almost everything.",
            "es": "Nada vegano salvo las patatas, hay queso en casi todo.",
            "fr": "Rien de végane à part les frites, il y a du fromage partout.",
            "it": "Niente di vegano tranne le patatine, c'è formaggio ovunque.",
            "de": "Außer Pommes nichts Veganes, überall ist Käse drin.",
        },
    },
    "service": {
        "pos": {
            "en": "Friendly, fast service and staff spoke good English.",
            "es": "Servicio rápido y amable, el personal hablaba inglés.",
            "fr": "Service rapide et chaleureux, le personnel parlait anglais.",
            "it": "Servizio veloce e cordiale, il personale parlava inglese.",
            "de": "Schneller, freundlicher Service und das Personal sprach gut Englisch.",
        },
        "neg": {
            "en": "Service was slow and a bit rude, we waited 40 minutes for mains.",
            "es": "El servicio fue lento y algo maleducado, esperamos 40 minutos el segundo plato.",
            "fr": "Service lent et un peu impoli, 40 minutes d'attente pour le plat.",
            "it": "Servizio lento e un po' scortese, 40 minuti di attesa per il secondo.",
            "de": "Der Service war langsam und etwas unfreundlich, 40 Minuten Wartezeit auf das Hauptgericht.",
        },
    },
    "price": {
        "pos": {
            "en": "Very good value for money, the set lunch menu is a bargain.",
            "es": "Muy buena relación calidad-precio, el menú del día es una ganga.",
            "fr": "Très bon rapport qualité-prix, la formule du midi est une affaire.",
            "it": "Ottimo rapporto qualità-prezzo, il menù pranzo è un affare.",
            "de": "Sehr gutes Preis-Leistungs-Verhältnis, das Mittagsmenü ist ein Schnäppchen.",
        },
        "neg": {
            "en": "Overpriced tourist trap, small portions for the price.",
            "es": "Demasiado caro, trampa para turistas, raciones pequeñas.",
            "fr": "Trop cher, piège à touristes, petites portions.",
            "it": "Troppo caro, trappola per turisti, porzioni piccole.",
            "de": "Überteuerte Touristenfalle, kleine Portionen für den Preis.",
        },
    },
    "breakfast": {
        "pos": {
            "en": "Perfect breakfast spot - excellent coffee and fresh pastries from 8am.",
            "es": "Perfecto para desayunar, café excelente y bollería recién hecha desde las 8.",
            "fr": "Parfait pour le petit-déjeuner, excellent café et viennoiseries fraîches dès 8h.",
            "it": "Perfetto per la colazione, caffè eccellente e cornetti freschi dalle 8.",
            "de": "Perfekt zum Frühstück, ausgezeichneter Kaffee und frisches Gebäck ab 8 Uhr.",
        },
        "neg": {
            "en": "Breakfast was disappointing, stale bread and lukewarm coffee.",
            "es": "El desayuno decepcionante, pan duro y café tibio.",
            "fr": "Petit-déjeuner décevant, pain rassis et café tiède.",
            "it": "Colazione deludente, pane raffermo e caffè tiepido.",
            "de": "Enttäuschendes Frühstück, altes Brot und lauwarmer Kaffee.",
        },
    },
    "atmosphere": {
        "pos": {
            "en": "Cosy atmosphere, quiet enough to talk - lovely for a dinner date.",
            "es": "Ambiente acogedor y tranquilo, ideal para una cena en pareja.",
            "fr": "Ambiance cosy et calme, idéal pour un dîner en amoureux.",
            "it": "Atmosfera accogliente e tranquilla, ideale per una cena romantica.",
            "de": "Gemütliche, ruhige Atmosphäre, ideal für ein Abendessen zu zweit.",
        },
        "neg": {
            "en": "Very noisy and crowded, tables packed too close together.",
            "es": "Muy ruidoso y lleno, las mesas demasiado juntas.",
            "fr": "Très bruyant et bondé, tables trop serrées.",
            "it": "Molto rumoroso e affollato, tavoli troppo vicini.",
            "de": "Sehr laut und voll, die Tische stehen zu eng.",
        },
    },
    "gluten": {
        "pos": {
            "en": "They have gluten-free bread and were careful about my coeliac allergy.",
            "es": "Tienen pan sin gluten y fueron cuidadosos con mi celiaquía.",
            "fr": "Ils ont du pain sans gluten et ont fait attention à ma maladie cœliaque.",
            "it": "Hanno pane senza glutine e sono stati attenti alla mia celiachia.",
            "de": "Es gibt glutenfreies Brot und man hat auf meine Zöliakie geachtet.",
        },
        "neg": {
            "en": "Could not guarantee anything gluten-free, not safe for coeliacs.",
            "es": "No podían garantizar nada sin gluten, no apto para celíacos.",
            "fr": "Aucune garantie sans gluten, pas sûr pour les cœliaques.",
            "it": "Nessuna garanzia senza glutine, non adatto ai celiaci.",
            "de": "Nichts garantiert glutenfrei, nicht sicher für Zöliakie-Betroffene.",
        },
    },
    "kids": {
        "pos": {
            "en": "Very family friendly, high chairs and a kids menu.",
            "es": "Muy familiar, tienen tronas y menú infantil.",
            "fr": "Très familial, chaises hautes et menu enfant.",
            "it": "Molto adatto alle famiglie, seggioloni e menù bambini.",
            "de": "Sehr familienfreundlich, Hochstühle und Kindermenü.",
        },
        "neg": {
            "en": "Not great with children, no space for a stroller.",
            "es": "No es buena opción con niños, no hay sitio para el carrito.",
            "fr": "Pas idéal avec des enfants, pas de place pour la poussette.",
            "it": "Non ideale con bambini, nessuno spazio per il passeggino.",
            "de": "Mit Kindern nicht ideal, kein Platz für den Kinderwagen.",
        },
    },
    "food": {
        "pos": {
            "en": "Delicious food made with fresh local ingredients, would come back.",
            "es": "Comida deliciosa con producto local y fresco, volveremos.",
            "fr": "Cuisine délicieuse avec des produits frais et locaux, on reviendra.",
            "it": "Cibo delizioso con ingredienti freschi e locali, torneremo.",
            "de": "Köstliches Essen aus frischen regionalen Zutaten, wir kommen wieder.",
        },
        "neg": {
            "en": "Food was bland and clearly microwaved.",
            "es": "La comida estaba sosa y claramente recalentada en microondas.",
            "fr": "Nourriture fade et visiblement réchauffée au micro-ondes.",
            "it": "Cibo insipido e chiaramente riscaldato al microonde.",
            "de": "Das Essen war fade und offensichtlich aus der Mikrowelle.",
        },
    },
}

NAMES = ["Laura M.", "Jordi P.", "Sophie L.", "Marco R.", "Anna K.", "Priya S.", "Tom W.",
         "Lucía G.", "Hans B.", "Aisha N.", "Chloé D.", "Rahul V.", "Elena C.", "Mateo F.",
         "Yuki T.", "Olivia H.", "Pierre A.", "Giulia B.", "Jonas S.", "Fatima Z."]


def generate_reviews(rest: dict, lang: str, n: int | None = None) -> list[dict]:
    seed = int(hashlib.md5(("rev" + rest["id"]).encode()).hexdigest(), 16)
    rnd = random.Random(seed)
    veg_friendly = rest.get("diet_vegetarian") in ("yes", "only") or rest.get("diet_vegan") in ("yes", "only")
    quality = rnd.uniform(0.45, 0.9) + (0.08 if veg_friendly else 0)
    local = lang if lang in ("es", "fr", "it", "de") else "en"
    n = n or rnd.randint(7, 12)
    out = []
    for i in range(n):
        positive = rnd.random() < quality
        aspects = rnd.sample(list(ASPECTS), k=2)
        # make vegetarian/vegan aspects more likely, and coherent with OSM diet tags
        if rnd.random() < 0.45:
            aspects[0] = "vegetarian" if rnd.random() < 0.7 else "vegan"
        if rest.get("breakfast") and rnd.random() < 0.3:
            aspects[1] = "breakfast"
        if aspects[0] == aspects[1]:
            aspects[1] = rnd.choice([a for a in ASPECTS if a != aspects[0]])
        rlang = local if rnd.random() < 0.55 else "en"
        sents = []
        for a in aspects:
            sent = "pos" if positive else "neg"
            if a in ("vegetarian", "vegan") and veg_friendly:
                sent = "pos" if rnd.random() < 0.88 else "neg"
            sents.append(sent)
        # star rating must agree with what the review says
        if all(s == "pos" for s in sents):
            rating = rnd.choice([4, 5, 5])
        elif all(s == "neg" for s in sents):
            rating = rnd.choice([1, 2, 2])
        else:
            rating = 3
        out.append({
            "author": rnd.choice(NAMES),
            "rating": rating,
            "lang": rlang,
            "text": " ".join(ASPECTS[a][s][rlang] for a, s in zip(aspects, sents)),
            "text_en": " ".join(ASPECTS[a][s]["en"] for a, s in zip(aspects, sents)),
            "source": "demo-synthetic",
            "created_at": f"2026-{rnd.randint(1, 9):02d}-{rnd.randint(1, 28):02d}",
        })
    return out
