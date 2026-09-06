"""Builds the manual index: markdown -> section chunks -> embeddings -> .npz

Run once:  python -m app.rag.index

Embeddings are local (all-MiniLM-L6-v2) so this costs nothing and works
offline. The retriever falls back to lexical scoring if the model is not
installed, which keeps tests and CI runnable without a 90 MB download.
"""
import json
import re
from dataclasses import asdict, dataclass

import numpy as np

from app.config import CHUNK_OVERLAP, CHUNK_WORDS, EMBED_MODEL, INDEX_PATH, MANUAL_DIR


@dataclass
class Chunk:
    chunk_id: str
    manual_id: str
    section: str
    text: str


def split_sections(md: str) -> list[tuple[str, str]]:
    """Split on '## ' headings, keeping the heading as the section label."""
    parts = re.split(r"^## ", md, flags=re.MULTILINE)
    out = []
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        body = body.strip()
        if body:
            out.append((head.strip(), body))
    return out


def window(text: str) -> list[str]:
    words = text.split()
    if len(words) <= CHUNK_WORDS:
        return [" ".join(words)]
    step = CHUNK_WORDS - CHUNK_OVERLAP
    return [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, len(words), step)
            if words[i:i + CHUNK_WORDS]]


def build_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(MANUAL_DIR.glob("*.md")):
        manual_id = path.stem
        for section, body in split_sections(path.read_text(encoding="utf-8")):
            for j, piece in enumerate(window(body)):
                chunks.append(Chunk(
                    chunk_id=f"{manual_id}::{section.split()[1] if len(section.split()) > 1 else section}::{j}",
                    manual_id=manual_id,
                    section=section,
                    text=piece,
                ))
    return chunks


def embed(texts: list[str]) -> np.ndarray | None:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers not installed — index saved without vectors "
              "(retriever will use lexical fallback)")
        return None
    model = SentenceTransformer(EMBED_MODEL)
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=True)


def main() -> None:
    chunks = build_chunks()
    vectors = embed([c.text for c in chunks])
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        INDEX_PATH,
        meta=np.array(json.dumps([asdict(c) for c in chunks])),
        vectors=vectors if vectors is not None else np.zeros((0, 0), dtype=np.float32),
    )
    print(f"indexed {len(chunks)} chunks from {MANUAL_DIR} -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
