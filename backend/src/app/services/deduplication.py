import chromadb
from chromadb.utils import embedding_functions
import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DeduplicationService:
    """
    Service for semantic deduplication of test cases using Vector Search (RAG).
    Stores successful test cases and retrieves them if a similar request comes in.
    """
    
    def __init__(self, persistence_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persistence_path)
        
        # Use default lightweight embedding model (all-MiniLM-L6-v2)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="test_cases_v1",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}  # Use Cosine similarity
        )

    def find_similar(self, query: str, threshold: float = 0.2) -> Optional[str]:
        """
        Search for a similar existing test case.
        Threshold: Distance score (lower is better for cosine distance in Chroma).
        0.0 = identical, 0.2 = very similar.
        """
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
        """
        Save a generated test case to the vector database.
        """
        try:
            self.collection.add(
                documents=[code],
                metadatas=[{"original_query": query}],
                ids=[str(uuid.uuid4())]
            )
            logger.info("Saved new test case to vector DB.")
        except Exception as e:
            logger.error(f"Failed to save to vector DB: {e}")
