"""Pre-translate the regional dish knowledge base and review phrases with the LLM
so interactive agent runs only need the LLM for freshly scraped menus.

Usage:  python -m app.ingest.warm_cache
"""
import asyncio

from app.agent.pipeline import translate_cached
from app.db import init_db
from app.knowledge.menus import REGIONAL
from app.knowledge.reviews import ASPECTS


async def main():
    init_db()
    for lang, dishes in REGIONAL.items():
        if lang == "en":
            continue
        _, st = await translate_cached([d[0] for d in dishes], lang)
        print(f"[warm] dishes {lang}: {st}", flush=True)
    for lang in ("es", "fr", "it", "de"):
        # reviews are translated sentence by sentence, so warming the phrases covers them
        phrases = [v[s][lang] for v in ASPECTS.values() for s in ("pos", "neg")]
        _, st = await translate_cached(phrases, lang, chunk=8)
        print(f"[warm] review phrases {lang}: {st}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
