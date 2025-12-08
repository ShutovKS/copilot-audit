import chromadb
from chromadb.utils import embedding_functions
import uuid
from typing import Optional
import logging
from src.app.core.config import get_settings

logger = logging.getLogger(__name__)

class DeduplicationService:
    """
    Service for semantic deduplication using ChromaDB (Server Mode).
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        try:
            # Connect to ChromaDB container
            self.client = chromadb.HttpClient(
                host=self.settings.CHROMA_HOST,
                port=self.settings.CHROMA_PORT
            )
            
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            
            self.collection = self.client.get_or_create_collection(
                name="test_cases_v1",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            # Fallback for tests/local without docker
            self.collection = None

    def find_similar(self, query: str, threshold: float = 0.2) -> Optional[str]:
        if not self.collection:
            return None
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=1
            )
            
            if not results["documents"] or not results["documents"][0]:
                return None
                
            distance = results["distances"][0][0]
            code = results["documents"][0][0]
            
            logger.info(f"Deduplication search: distance={distance}")
            
            if distance < threshold:
                return code
            
            return None
            
        except Exception as e:
            logger.error(f"Deduplication query failed: {e}")
            return None

    def save(self, query: str, code: str) -> None:
        if not self.collection:
            return
            
        try:
            self.collection.add(
                documents=[code],
                metadatas=[{"original_query": query}],
                ids=[str(uuid.uuid4())]
            )
            logger.info("Saved new test case to vector DB.")
        except Exception as e:
            logger.error(f"Failed to save to vector DB: {e}")
