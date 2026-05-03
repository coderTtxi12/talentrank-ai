"""Chroma vector store wrapper for RAG.

Persistent client + OpenAI embedding function (defaults to text-embedding-ada-002).
Provides:
    - `get_collection`: get or create a collection.
    - `upsert_documents`: store/update chunks.
    - `semantic_search`: top-k retrieval over a collection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

import chromadb
from chromadb.api.types import EmbeddingFunction
from chromadb.utils import embedding_functions

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def _embedding_function() -> EmbeddingFunction:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings.")
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name=settings.OPENAI_EMBEDDING_MODEL,
    )


@lru_cache
def get_client() -> chromadb.api.ClientAPI:
    """Process-wide Chroma persistent client rooted at ``CHROMA_PERSIST_DIR``."""

    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_collection(name: Optional[str] = None):
    """Get or create a collection with OpenAI embedding function and cosine HNSW space."""

    coll_name = name or settings.CHROMA_COLLECTION_KB
    client = get_client()
    return client.get_or_create_collection(
        name=coll_name,
        embedding_function=_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def upsert_documents(
    documents: List[str],
    ids: List[str],
    metadatas: Optional[List[Dict[str, Any]]] = None,
    *,
    collection_name: Optional[str] = None,
) -> int:
    """Upsert chunks into Chroma. Returns number of records persisted."""

    coll = get_collection(collection_name)
    coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Upserted %d docs into collection %s", len(documents), coll.name)
    return len(documents)


def _float_list(vec: Any) -> List[float]:
    if vec is None:
        return []
    if hasattr(vec, "tolist"):
        vec = vec.tolist()
    return [float(x) for x in vec]


def embed_text(text: str) -> List[float]:
    """Dense embedding for `text` using the same model Chroma uses for this collection."""

    ef = _embedding_function()
    batch = ef([text])
    if not batch:
        return []
    return _float_list(batch[0])


def semantic_search(
    query: str,
    *,
    k: Optional[int] = None,
    collection_name: Optional[str] = None,
    where: Optional[Dict[str, Any]] = None,
    include_embeddings: bool = False,
) -> List[Dict[str, Any]]:
    """Run a top-k semantic search and return normalized hits.

    With ``include_embeddings=True``, each hit includes an ``embedding`` key:
    stored vector Chroma associates with that chunk (same space as cosine distance).
    """

    coll = get_collection(collection_name)
    n = k if k is not None else settings.RAG_TOP_K
    inc: List[Any] = ["documents", "metadatas", "distances"]
    if include_embeddings:
        inc.append("embeddings")

    res = coll.query(query_texts=[query], n_results=n, where=where, include=inc)

    documents = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]
    embeddings = ((res.get("embeddings") or [[]])[0]) if include_embeddings else []

    hits: List[Dict[str, Any]] = []
    for i, doc in enumerate(documents):
        hit: Dict[str, Any] = {
            "id": ids[i] if i < len(ids) else None,
            "document": doc,
            "metadata": metadatas[i] if i < len(metadatas) else {},
            "distance": distances[i] if i < len(distances) else None,
        }
        if include_embeddings and i < len(embeddings):
            hit["embedding"] = _float_list(embeddings[i])
        hits.append(hit)
    return hits
