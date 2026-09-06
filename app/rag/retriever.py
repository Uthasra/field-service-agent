"""Loads the index once and answers similarity queries.

Two modes, chosen automatically:
  vector  — cosine over all-MiniLM-L6-v2 embeddings (normal path)
  lexical — token overlap scoring (fallback when no vectors were built)
"""
import json
import math
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from app.config import EMBED_MODEL, INDEX_PATH, TOP_K

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@lru_cache(maxsize=1)
def _load():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"{INDEX_PATH} missing. Run: python -m app.rag.index")
    blob = np.load(INDEX_PATH, allow_pickle=False)
    meta = json.loads(str(blob["meta"]))
    vectors = blob["vectors"]
    return meta, (vectors if vectors.size else None)


@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def _lexical_scores(query: str, meta: list[dict]) -> np.ndarray:
    q = Counter(tokenize(query))
    docs = [Counter(tokenize(m["section"] + " " + m["text"])) for m in meta]
    df = Counter()
    for d in docs:
        df.update(d.keys())
    n = len(docs)
    scores = []
    for d in docs:
        s = 0.0
        for term, qc in q.items():
            if term in d:
                idf = math.log((n + 1) / (df[term] + 0.5))
                s += qc * idf * (d[term] / (d[term] + 1.5))
        scores.append(s)
    return np.array(scores)


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    meta, vectors = _load()
    if vectors is not None:
        qv = _encoder().encode([query], normalize_embeddings=True)[0]
        scores = vectors @ qv
        mode = "vector"
    else:
        scores = _lexical_scores(query, meta)
        mode = "lexical"
    order = np.argsort(-scores)[:top_k]
    return [
        {**meta[i], "score": round(float(scores[i]), 4), "mode": mode}
        for i in order if scores[i] > 0
    ]
