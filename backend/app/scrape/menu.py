"""Menu reader: fetches a restaurant's own website, follows its menu link and
extracts dishes + prices.

Strategy:
  1. httpx GET of the menu URL (OSM `website:menu`) or homepage (`website`).
  2. If the page is a JS shell (little visible text), render it with Playwright.
  3. Find a link that looks like a menu ("menu", "carta", "carte", "speisekarte"...)
     and read that page too.
  4. Extract "dish .... 12,50 €" style lines with regexes.
Only the restaurant's own public site is visited (robots-friendly, low volume).
"""
import asyncio
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EuroEatAgent/1.0"
MENU_WORDS = re.compile(
    r"\b(men[uú]s?|carta|la carte|carte|speisekarte|karte|cardápio|ementa|menukaart|kaart|"
    r"jídelní|food|eat|comida|cuina|dishes|platos|piatti)\b", re.I)
PRICE = r"(?:€\s?\d{1,3}(?:[.,]\d{1,2})?|\d{1,3}(?:[.,]\d{1,2})?\s?(?:€|eur\b|euros?\b|£|chf|kč|czk|zł|pln|kr|ft|huf))"
LINE_PRICE = re.compile(rf"^(?P<name>[^\d€£]{{3,80}}?)[\s.\-–:·…]*?(?P<price>{PRICE})\s*$", re.I)
PRICE_ONLY = re.compile(rf"^\s*(?P<price>{PRICE})\s*$", re.I)
NUM = re.compile(r"\d{1,3}(?:[.,]\d{1,2})?")

_playwright_lock = asyncio.Lock()


def _parse_price(s: str) -> float | None:
    m = NUM.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _visible_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        t.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    return [ln for ln in lines if ln]


CURRENCY_ONLY = re.compile(r"^\s*(€|eur|euros?|£|chf|kč|czk|zł|pln|kr|ft|huf)\s*$", re.I)
BARE_DECIMAL = re.compile(r"^\s*(?:€\s?)?\d{1,3}[.,]\d{2}\s*$")


def _merge_currency_lines(lines: list[str]) -> list[str]:
    """Sites often render '16,50' and '€' as separate DOM nodes."""
    out = []
    for ln in lines:
        if CURRENCY_ONLY.match(ln) and out:
            out[-1] = f"{out[-1]} {ln.strip()}"
        else:
            out.append(ln)
    return out


def _is_name(ln: str) -> bool:
    return (3 <= len(ln) <= 70 and len(ln.split()) <= 10 and not NUM.fullmatch(ln)
            and not ln.endswith(".") and sum(c.isalpha() for c in ln) >= 3)


def extract_items(lines: list[str], currency: str) -> list[dict]:
    items = []
    pending_name, gap, pending_price = None, 0, None
    for ln in _merge_currency_lines(lines):
        if len(ln) > 200:
            continue
        m = LINE_PRICE.match(ln)
        if m:
            name = m.group("name").strip(" .-–:·…|")
            price = _parse_price(m.group("price"))
            if name and price and 0.5 <= price <= 400 and _is_name(name):
                items.append({"name": name, "price": price, "currency": currency})
            pending_name, pending_price = None, None
            continue
        if PRICE_ONLY.match(ln) or BARE_DECIMAL.match(ln):
            price = _parse_price(ln)
            if not price or not 0.5 <= price <= 400:
                continue
            if pending_name and gap <= 2:  # name, [description], price
                items.append({"name": pending_name, "price": price, "currency": currency})
                pending_name = None
            else:  # price printed before the name
                pending_price = price
            continue
        if _is_name(ln):
            if pending_price is not None:
                items.append({"name": ln, "price": pending_price, "currency": currency})
                pending_price = None
                pending_name = None
            else:
                pending_name, gap = ln, 0
        else:
            gap += 1  # a long description line between name and price
    # de-dup
    seen, out = set(), []
    for it in items:
        k = it["name"].lower()
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out[:40]


def _menu_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base).netloc
    links = []
    for a in soup.find_all("a", href=True):
        label = (a.get_text(" ") or "") + " " + a["href"]
        if MENU_WORDS.search(label):
            href = urljoin(base, a["href"]).split("#")[0]
            if not href:
                continue
            if href.lower().endswith(".pdf"):
                links.append(href)
            elif urlparse(href).netloc == host and href.rstrip("/") != base.rstrip("/"):
                links.append(href)
    # html links first, pdfs last (we report but can't parse pdfs)
    links = sorted(dict.fromkeys(links), key=lambda u: u.lower().endswith(".pdf"))
    return links[:3]


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    for verify in (True, False):  # many small restaurant sites have broken TLS certs
        try:
            if verify:
                r = await client.get(url)
            else:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True, verify=False,
                                             headers={"User-Agent": UA}) as insecure:
                    r = await insecure.get(url)
            if r.status_code < 400 and "html" in r.headers.get("content-type", ""):
                return r.text
            return None
        except httpx.ConnectError as e:
            if "CERTIFICATE" not in str(e):
                return None
        except Exception:
            return None
    return None


async def _pdf_lines(client: httpx.AsyncClient, url: str) -> list[str]:
    try:
        import io
        from pypdf import PdfReader
        r = await client.get(url)
        if r.status_code >= 400 or len(r.content) > 15_000_000:
            return []
        reader = PdfReader(io.BytesIO(r.content))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:6])
        return [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]
    except Exception:
        return []


async def _render(url: str, timeout_ms=15000) -> str | None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None
    async with _playwright_lock:  # one browser at a time keeps memory sane
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=UA)
                await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                html = await page.content()
                await browser.close()
                return html
        except Exception:
            return None


async def scrape_menu(rest: dict, currency: str, use_browser=True) -> dict:
    """Returns {items, source_url, menu_page, pdf, method} - items may be empty."""
    start = rest.get("menu_url") or rest.get("website")
    result = {"items": [], "source_url": start, "menu_page": None, "pdf": None, "method": None}
    if not start:
        return result
    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": UA}) as client:
        html = await _fetch(client, start)
        method = "http"
        if (html is None or len(_visible_lines(html)) < 15) and use_browser:
            html = await _render(start) or html
            method = "playwright"
        if not html:
            return result
        candidates = [(start, html)]
        for link in _menu_links(html, start):
            if link.lower().endswith(".pdf"):
                result["pdf"] = result["pdf"] or link
                continue
            sub = await _fetch(client, link)
            if (sub is None or len(_visible_lines(sub)) < 15) and use_browser:
                sub = await _render(link) or sub
            if sub:
                candidates.append((link, sub))
        best = []
        for url, page in candidates:
            items = extract_items(_visible_lines(page), currency)
            if len(items) > len(best):
                best = items
                result["menu_page"] = url
        if len(best) < 4 and result["pdf"]:
            items = extract_items(await _pdf_lines(client, result["pdf"]), currency)
            if len(items) > len(best):
                best = items
                result["menu_page"] = result["pdf"]
                method = "pdf"
        result["items"] = best
        result["method"] = method
        if not result["menu_page"] and len(candidates) > 1:
            result["menu_page"] = candidates[1][0]
    return result
