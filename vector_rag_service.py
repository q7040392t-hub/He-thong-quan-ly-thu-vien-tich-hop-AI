"""Semantic / Vector RAG for SmartLibrary.

This module is intentionally dependency-light: it reuses the installed Google GenAI
SDK to create embeddings and computes cosine similarity with pure Python.  The
existing BM25 RAG remains available and can be combined with this retriever in
HYBRID mode.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable

try:
    from google.genai import types
except Exception:  # pragma: no cover - the caller will fall back to BM25
    types = None


BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / ".vector_rag_cache.json"


def _clean(value):
    return " ".join(str(value or "").split())


def book_to_text(book):
    """Build a semantic document from one MySQL book row."""
    parts = [
        f"Mã sách: {_clean(book.get('id'))}",
        f"Tên sách: {_clean(book.get('title'))}",
        f"Tác giả: {_clean(book.get('author'))}",
        f"Thể loại: {_clean(book.get('category'))}",
        f"ISBN: {_clean(book.get('isbn'))}",
        f"Nhà xuất bản: {_clean(book.get('publisher'))}",
        f"Vị trí: {_clean(book.get('location'))}",
        f"Mô tả: {_clean(book.get('description'))}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _stable_key(prefix: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return f"{prefix}:{digest}"


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _vector_values(embedding):
    values = getattr(embedding, "values", None)
    if values is None and isinstance(embedding, dict):
        values = embedding.get("values")
    return [float(x) for x in (values or [])]


class VectorRAGService:
    """Gemini-embedding based semantic retriever with a small disk cache."""

    def __init__(self, client, model=None, dimensions=None):
        self.client = client
        self.model = (model or os.getenv("RAG_EMBEDDING_MODEL", "gemini-embedding-001")).strip()
        try:
            self.dimensions = int(dimensions or os.getenv("RAG_EMBEDDING_DIMENSIONS", "768"))
        except Exception:
            self.dimensions = 768
        self.dimensions = max(128, min(self.dimensions, 3072))
        self.enabled = bool(client and types)
        self._cache = self._load_cache()

    def _load_cache(self):
        if not CACHE_FILE.exists():
            return {}
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("model") != self.model or int(data.get("dimensions", 0)) != self.dimensions:
                return {}
            return data.get("vectors", {}) or {}
        except Exception:
            return {}

    def _save_cache(self):
        try:
            payload = {
                "model": self.model,
                "dimensions": self.dimensions,
                "vectors": self._cache,
            }
            CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _embed(self, texts: Iterable[str], task_type=None):
        texts = list(texts)
        if not texts or not self.enabled:
            return []
        kwargs = {"output_dimensionality": self.dimensions}
        if task_type:
            kwargs["task_type"] = task_type
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts if len(texts) > 1 else texts[0],
            config=types.EmbedContentConfig(**kwargs),
        )
        embeddings = getattr(response, "embeddings", None) or []
        return [_vector_values(item) for item in embeddings]

    def _document_vectors(self, records, prefix, text_fn):
        vectors = []
        missing_texts = []
        missing_positions = []
        keys = []
        for idx, record in enumerate(records):
            text = text_fn(record)
            key = _stable_key(prefix, text)
            keys.append(key)
            cached = self._cache.get(key)
            vectors.append(cached)
            if not cached:
                missing_texts.append(text)
                missing_positions.append(idx)

        # Keep each request moderate. Only changed/new documents are embedded.
        for start in range(0, len(missing_texts), 50):
            batch_texts = missing_texts[start:start + 50]
            batch_positions = missing_positions[start:start + 50]
            batch_vectors = self._embed(batch_texts, task_type="RETRIEVAL_DOCUMENT")
            for pos, vec in zip(batch_positions, batch_vectors):
                if vec:
                    vectors[pos] = vec
                    self._cache[keys[pos]] = vec
        if missing_texts:
            self._save_cache()
        return vectors

    def rank_books(self, books, query, top_k=3):
        if not self.enabled or not books or not str(query).strip():
            return []
        query_vecs = self._embed([str(query)], task_type="RETRIEVAL_QUERY")
        if not query_vecs or not query_vecs[0]:
            return []
        doc_vectors = self._document_vectors(books, "book", book_to_text)
        ranked = []
        for book, vec in zip(books, doc_vectors):
            score = _cosine(query_vecs[0], vec)
            item = dict(book)
            item["_vector_score"] = round(float(score), 6)
            ranked.append(item)
        ranked.sort(key=lambda x: x.get("_vector_score", 0), reverse=True)
        # Negative/zero similarity is not useful as RAG context.
        return [b for b in ranked if b.get("_vector_score", 0) > 0][:int(top_k)]

    def rank_policy_chunks(self, chunks, query, top_k=3):
        if not self.enabled or not chunks or not str(query).strip():
            return []
        records = [{"text": str(c)} for c in chunks]
        query_vecs = self._embed([str(query)], task_type="RETRIEVAL_QUERY")
        if not query_vecs or not query_vecs[0]:
            return []
        doc_vectors = self._document_vectors(records, "policy", lambda x: x["text"])
        ranked = []
        for idx, (record, vec) in enumerate(zip(records, doc_vectors)):
            score = _cosine(query_vecs[0], vec)
            ranked.append({"text": record["text"], "score": round(float(score), 6), "index": idx, "vector_score": round(float(score), 6)})
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return [x for x in ranked if x["score"] > 0][:int(top_k)]
