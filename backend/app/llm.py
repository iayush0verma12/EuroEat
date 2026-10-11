"""Thin async client for a local Ollama server."""
import json
import math
import os
import re

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EUROEAT_MODEL", "llama3.2")
EMBED_MODEL = os.environ.get("EUROEAT_EMBED_MODEL", "nomic-embed-text")
NUM_CTX = int(os.environ.get("EUROEAT_NUM_CTX", "4096"))

LANG_NAMES = {
    "es": "Spanish", "ca": "Catalan", "fr": "French", "it": "Italian", "de": "German",
    "pt": "Portuguese", "nl": "Dutch", "cs": "Czech", "el": "Greek", "da": "Danish",
    "sv": "Swedish", "pl": "Polish", "hu": "Hungarian", "no": "Norwegian", "en": "English",
}


async def status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            return {"online": True, "model": MODEL, "models": models}
    except Exception:
        return {"online": False, "model": MODEL, "models": []}


async def chat(messages, fmt=None, temperature=0.2, timeout=120) -> str | None:
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": NUM_CTX},
    }
    if fmt:
        payload["format"] = fmt
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except Exception:
        return None


async def chat_stream(messages, temperature=0.4, timeout=180):
    """Yields content chunks. Yields nothing if Ollama is unavailable."""
    payload = {"model": MODEL, "messages": messages, "stream": True,
               "options": {"temperature": temperature, "num_ctx": NUM_CTX}}
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            async with c.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line)
                    chunk = msg.get("message", {}).get("content")
                    if chunk:
                        yield chunk
                    if msg.get("done"):
                        break
    except Exception:
        return


async def chat_json(messages, timeout=120):
    out = await chat(messages, fmt="json", timeout=timeout)
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}|\[.*\]", out, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


async def translate_batch(texts: list[str], src_lang: str) -> list[str] | None:
    """Translate a list of short strings to English in a single LLM call."""
    if not texts:
        return []
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    lang = LANG_NAMES.get(src_lang, src_lang)
    res = await chat_json([
        {"role": "system", "content": (
            "You are a precise restaurant-menu and review translator. Translate each numbered "
            f"line from {lang} (it may also contain Catalan or English) into natural English. "
            'Keep dish names short. Reply ONLY with JSON: {"translations": ["...", "..."]} '
            "with exactly one entry per input line, in order.")},
        {"role": "user", "content": numbered},
    ])
    if not res:
        return None
    arr = res.get("translations") if isinstance(res, dict) else res
    if not isinstance(arr, list) or len(arr) != len(texts):
        return None
    return [str(a) for a in arr]


_embed_cache: dict[str, list[float]] = {}


async def embed(texts: list[str]) -> list[list[float]] | None:
    todo = list(dict.fromkeys(t for t in texts if t not in _embed_cache))
    if todo:
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": todo})
                r.raise_for_status()
                for t, v in zip(todo, r.json()["embeddings"]):
                    _embed_cache[t] = v
        except Exception:
            return None
    return [_embed_cache[t] for t in texts]


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
