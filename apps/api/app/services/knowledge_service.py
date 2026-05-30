"""Knowledge base ingestion + search.

- Extract text from uploads (txt/md/pdf).
- Chunk with overlap.
- Embed chunks locally via sentence-transformers (all-MiniLM-L6-v2, 384d).
- Store points in a per-workspace Qdrant collection.
- Search by embedding the query and pulling top-K from the workspace collection.

We use sentence-transformers (PyTorch-based) because:
  - Groq doesn't offer an embeddings API, so we can't reuse our LLM key.
  - fastembed's Python 3.14 wheels are blocked by Rust dependencies (mmh3,
    py-rust-stemmers) that don't have 3.14 builds yet.
  - sentence-transformers + PyTorch both have Python 3.14 wheels.

First call to `_get_embedder()` downloads the model (~80MB) into
~/.cache/huggingface/ and is cached for all subsequent calls.
"""
from __future__ import annotations

import io
import logging
import re
import uuid
from typing import Iterable

from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionFactory
from app.models import KnowledgeDoc

log = logging.getLogger(__name__)

_VECTOR_SIZE = 384

_embedder = None
_qdrant = QdrantClient(url=settings.qdrant_url)


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        log.info("Loading embedding model %s (first use downloads ~80MB)", settings.embedding_model)
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def _collection_name(workspace_id: int) -> str:
    return f"ws_{workspace_id}_kb"


def _ensure_collection(workspace_id: int) -> str:
    name = _collection_name(workspace_id)
    existing = {c.name for c in _qdrant.get_collections().collections}
    if name not in existing:
        _qdrant.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )
    return name


def _extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return content.decode("utf-8", errors="replace")


def _chunk_text(text: str, chunk_size: int = 450, overlap: int = 80) -> list[str]:
    """Character-window chunking with overlap.

    Smaller windows keep each chunk topically focused, which matters for
    short factual lookups (hours, pricing) where a big chunk spanning
    several sections dilutes the embedding. Adequate for V1; swap to
    recursive/semantic splitting later.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _embed(texts: Iterable[str]) -> list[list[float]]:
    embedder = _get_embedder()
    text_list = list(texts)
    if not text_list:
        return []
    vectors = embedder.encode(text_list, normalize_embeddings=True, show_progress_bar=False)
    return [vec.tolist() for vec in vectors]


def ingest_document_sync(session: Session, doc: KnowledgeDoc, content: bytes) -> None:
    """Synchronous ingest: extract -> chunk -> embed -> upsert. Updates doc.status."""
    try:
        text = _extract_text(doc.filename, content)
        chunks = _chunk_text(text)
        if not chunks:
            doc.status = "failed"
            doc.chunk_count = 0
            session.commit()
            return
        collection = _ensure_collection(doc.workspace_id)
        vectors = _embed(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i],
                payload={
                    "doc_id": doc.id,
                    "chunk_idx": i,
                    "text": chunks[i],
                    "filename": doc.filename,
                },
            )
            for i in range(len(chunks))
        ]
        _qdrant.upsert(collection_name=collection, points=points)
        doc.status = "ready"
        doc.chunk_count = len(chunks)
        doc.qdrant_collection = collection
        session.commit()
    except Exception:
        log.exception("Knowledge ingest failed for doc id=%s", doc.id)
        doc.status = "failed"
        session.commit()


def ingest_document_bg(doc_id: int, content: bytes) -> None:
    """Background-task entrypoint. Opens its own session because the request session
    has already closed by the time this runs."""
    with SessionFactory() as session:
        doc = session.get(KnowledgeDoc, doc_id)
        if doc is None:
            return
        ingest_document_sync(session, doc, content)


def delete_document_vectors(workspace_id: int, doc_id: int) -> None:
    """Remove all Qdrant points belonging to a doc."""
    collection = _collection_name(workspace_id)
    try:
        _qdrant.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
    except UnexpectedResponse:
        return


def search(workspace_id: int, query: str, limit: int = 5) -> list[dict]:
    collection = _collection_name(workspace_id)
    existing = {c.name for c in _qdrant.get_collections().collections}
    if collection not in existing:
        return []
    [query_vec] = _embed([query])
    response = _qdrant.query_points(
        collection_name=collection, query=query_vec, limit=limit
    )
    return [
        {
            "doc_id": int(r.payload.get("doc_id", 0)),
            "filename": str(r.payload.get("filename", "")),
            "chunk_idx": int(r.payload.get("chunk_idx", 0)),
            "text": str(r.payload.get("text", "")),
            "score": float(r.score),
        }
        for r in response.points
    ]
