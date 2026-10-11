import { AlertTriangle, Bot, Database, Layers, ListChecks } from 'lucide-react'

export default function About() {
  return (
    <div className="page-grid">
      <div className="card section" style={{ gridColumn: '1 / -1' }}>
        <h3><Bot size={17} /> What is EuroEat?</h3>
        <p className="muted" style={{ lineHeight: 1.65, maxWidth: 880, margin: 0 }}>
          EuroEat is an AI agent that recommends restaurants to travellers in European cities, with a focus on
          vegetarian food. Tell it where you are going and which meals you need; it shows every step it takes —
          from finding candidate restaurants to reading and translating their menus and weighing their reviews —
          and ends with concrete dishes, prices and links. You can then order online or book a table, with the best
          coupon applied automatically.
        </p>
      </div>

      <div className="card section">
        <h3><ListChecks size={17} /> The agent pipeline</h3>
        <ol className="pipeline-list">
          <li><span><b>Understand</b> — LLM extracts city, diet, meals, budget and special needs (rules as fallback).</span></li>
          <li><span><b>Identify</b> — query ~77k OpenStreetMap restaurants for the city; filter by diet tags & cuisine and by meal (opening hours, cafés for breakfast).</span></li>
          <li><span><b>Shortlist</b> — score by veg-tag strength, website/menu availability, cuisine & budget fit and distance.</span></li>
          <li><span><b>Read menus</b> — visit each restaurant's own site (httpx → Playwright for JS → PDF parsing) and extract dishes + prices.</span></li>
          <li><span><b>Translate</b> — the local LLM translates dish names to English (cached), then dishes are classified as vegetarian.</span></li>
          <li><span><b>Reviews</b> — split positive (4-5★) and negative (1-2★), translate non-English reviews.</span></li>
          <li><span><b>Context search</b> — semantic search (nomic-embed-text) for reviews about your needs: gluten-free, kids, quiet…</span></li>
          <li><span><b>Menu items & prices</b> — pick regular dishes that fit the diet and meal.</span></li>
          <li><span><b>Suggest</b> — rank and stream a written recommendation grounded only in the collected data.</span></li>
        </ol>
      </div>

      <div className="card section">
        <h3><Layers size={17} /> Stack</h3>
        <div className="grid" style={{ gap: 8, fontSize: 13.5 }}>
          <div><b>Frontend</b> <span className="muted">React + TypeScript (Vite), three.js for the 3D Europe map and cityscapes</span></div>
          <div><b>Backend</b> <span className="muted">Python FastAPI, streaming agent events over Server-Sent Events</span></div>
          <div><b>AI</b> <span className="muted">Ollama — llama3.2 (chat/translation) and nomic-embed-text (review search)</span></div>
          <div><b>Database</b> <span className="muted">SQLite: restaurants, menus, reviews, translations cache, buildings, users, orders</span></div>
          <div><b>Scraping</b> <span className="muted">httpx + BeautifulSoup, Playwright (Chromium) for JS sites, pypdf for PDF menus</span></div>
        </div>
        <h3 style={{ marginTop: 22 }}><Database size={17} /> Data sources</h3>
        <div className="grid" style={{ gap: 8, fontSize: 13.5 }}>
          <div><b>Restaurants & buildings</b> <span className="muted">© OpenStreetMap contributors (ODbL) via the Overpass API</span></div>
          <div><b>Menus</b> <span className="muted">restaurants' own websites; estimated from a regional dish knowledge base when unavailable</span></div>
          <div><b>Reviews</b> <span className="muted">sample multilingual review dataset (see limitations)</span></div>
          <div><b>Geocoding</b> <span className="muted">Nominatim (town lookup on the Stats map)</span></div>
        </div>
      </div>

      <div className="card section" style={{ gridColumn: '1 / -1' }}>
        <h3><AlertTriangle size={17} color="var(--amber)" /> Limitations & assumptions</h3>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18, fontSize: 13.5 }}>
          <ul className="muted" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li>Reviews come from a synthetic sample dataset: Google/TripAdvisor/Yelp don't offer free review APIs and forbid scraping. The pipeline works unchanged with a real provider.</li>
            <li>Many restaurant sites are down, image-only or have no prices; those menus are <i>estimated</i> and clearly labelled.</li>
            <li>Ordering, booking and coupons are simulated — no payment or real reservation happens.</li>
            <li>A CPU-only local LLM makes first runs slow (minutes); translations are cached so repeat runs are fast.</li>
          </ul>
          <ul className="muted" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
            <li>“Vegetarian” = OSM diet tags first, then veg-friendly cuisines; dish-level detection uses multilingual meat/fish keywords.</li>
            <li>Breakfast = cafés, places tagged breakfast or opening before 10:00; dinner = open after 21:00 or no hours listed.</li>
            <li>Coverage is the central area of 32 major cities; other towns can be checked live on the Stats map.</li>
            <li>Price levels are estimated when OSM has no price information.</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
