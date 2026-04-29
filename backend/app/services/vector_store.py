"""Chroma vector store wrapper for RAG.

Persistent client + OpenAI embedding function (defaults to text-embedding-ada-002).
Provides:
    - `get_collection`: get or create a collection.
    - `upsert_documents`: store/update chunks.
    - `semantic_search`: top-k retrieval over a collection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

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
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_collection(name: Optional[str] = None):
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


def semantic_search(
    query: str,
    *,
    k: Optional[int] = None,
    collection_name: Optional[str] = None,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run a top-k semantic search and return normalized hits."""

    coll = get_collection(collection_name)
    n = k if k is not None else settings.RAG_TOP_K
    res = coll.query(query_texts=[query], n_results=n, where=where)

    documents = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]

    hits: List[Dict[str, Any]] = []
    for i, doc in enumerate(documents):
        hits.append(
            {
                "id": ids[i] if i < len(ids) else None,
                "document": doc,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )
    return hits
