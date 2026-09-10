"""Deterministic local text embedding.

Chosen over a hosted embedding API or a transformer model so retrieval works
with no API key and no multi-hundred-megabyte dependency (the backend runs on
a serverless runtime with a package size limit).

Text is hashed into a fixed-width bag of word unigrams, word bigrams and
character 4-grams with sub-linear term weighting, then L2-normalised so cosine
distance in pgvector is meaningful. It captures lexical and morphological
overlap rather than deep semantics, which is why retrieval is hybrid: this is
fused with Postgres full-text ranking in rag_service.
"""

import hashlib
import math
import re
from collections import Counter

from app.models.document import EMBEDDING_DIM

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "is", "are",
    "was", "were", "be", "with", "that", "this", "it", "as", "at", "by", "from",
}


def _bucket(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % EMBEDDING_DIM


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


def embed(text: str) -> list[float]:
    """Return an L2-normalised EMBEDDING_DIM vector for `text`."""
    words = tokenize(text)
    features: Counter[str] = Counter()

    for w in words:
        features[f"w:{w}"] += 1
    for a, b in zip(words, words[1:]):
        features[f"b:{a}_{b}"] += 1

    compact = " ".join(words)
    for i in range(len(compact) - 3):
        gram = compact[i:i + 4]
        if " " not in gram:
            features[f"c:{gram}"] += 1

    vec = [0.0] * EMBEDDING_DIM
    for feature, count in features.items():
        # sub-linear weighting keeps long documents from dominating
        vec[_bucket(feature)] += 1.0 + math.log(count)

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        # a zero vector has undefined cosine distance; use a stable unit vector
        vec[0] = 1.0
        return vec
    return [v / norm for v in vec]


def chunk_text(text: str, *, target_chars: int = 900, overlap: int = 150) -> list[str]:
    """Split on paragraph boundaries, packing to ~target_chars with overlap."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > target_chars:
            chunks.append(buf)
            buf = (buf[-overlap:] + "\n\n" + para) if overlap else para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)

    # a single oversized paragraph still needs splitting
    out: list[str] = []
    for c in chunks:
        while len(c) > target_chars * 2:
            out.append(c[: target_chars * 2])
            c = c[target_chars * 2 - overlap:]
        out.append(c)
    return out or [text[:target_chars]]
