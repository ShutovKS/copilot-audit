import logging
import uuid

import chromadb
from chromadb.utils import embedding_functions

from src.app.core.config import get_settings

logger = logging.getLogger(__name__)

class DeduplicationService:
    """
    Service for semantic deduplication using ChromaDB (Server Mode).
    """

    def __init__(self, embedding_function=None):
        self.settings = get_settings()

        try:
            self.client = chromadb.HttpClient(
                host=self.settings.CHROMA_HOST,
                port=self.settings.CHROMA_PORT
            )

            if embedding_function:
                self.embedding_fn = embedding_function
            else:
                self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

            self.collection = self.client.get_or_create_collection(
                name="test_cases_v1",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self.collection = None

    def find_similar(self, query: str, threshold: float = 0.3) -> str | None:
        if not self.collection:
            return None

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=1,
                include=["metadatas", "distances"]
            )

            if not results["ids"][0]:
                return None

            distance = results["distances"][0][0]
            metadata = results["metadatas"][0][0]
            code = metadata.get("code")

            logger.info(f"Deduplication search: closest distance={distance:.4f} with threshold={threshold}")

            if distance < threshold and code:
                logger.info("✅ Found semantically similar request in cache. Reusing code.")
                return code

            return None

        except Exception as e:
            logger.error(f"Deduplication query failed: {e}", exc_info=True)
            return None

    def save(self, query: str, code: str) -> None:
        if not self.collection:
            return

        try:
            # The document for embedding is the user's request (query)
            # The code is stored as metadata
            self.collection.add(
                documents=[query],
                metadatas=[{"code": code, "original_query": query}],
                ids=[str(uuid.uuid4())]
            )
            logger.info("Saved new test case query and code to vector DB.")
        except Exception as e:
            logger.error(f"Failed to save to vector DB: {e}", exc_info=True)
