import logging
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import chromadb
from chromadb.utils import embedding_functions

from src.app.core.config import get_settings

logger = logging.getLogger(__name__)


def _extract_domain(url: str | None) -> str | None:
	if not url:
		return None
	try:
		parsed = urlparse(url)
		return parsed.netloc or None
	except Exception:
		return None


class KnowledgeBaseService:
	"""Long-term memory for QA insights.

	Stores small "lessons" extracted after successful fixes.
	Uses a dedicated ChromaDB collection separate from test deduplication.
	"""

	COLLECTION_NAME = "qa_insights"

	def __init__(self, embedding_function=None):
		self.settings = get_settings()

		try:
			self.client = chromadb.HttpClient(
				host=self.settings.CHROMA_HOST,
				port=self.settings.CHROMA_PORT,
			)

			if embedding_function:
				self.embedding_fn = embedding_function
			else:
				self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

			self.collection = self.client.get_or_create_collection(
				name=self.COLLECTION_NAME,
				embedding_function=self.embedding_fn,
				metadata={"hnsw:space": "cosine"},
			)
		except Exception as e:
			logger.error(f"KnowledgeBaseService: Failed to connect to ChromaDB: {e}")
			self.collection = None

	def learn_lesson(self, url: str | None, original_error: str, fix_summary: str) -> None:
		"""Persist a lesson to long-term memory."""
		if not self.collection:
			return

		url = (url or "").strip() or None
		domain = _extract_domain(url)
		original_error = (original_error or "").strip()
		fix_summary = (fix_summary or "").strip()

		if not fix_summary:
			return

		# Embed a combination of URL + error, so we can recall similar situations later.
		doc_text = f"URL: {url or 'N/A'} | Error: {original_error}"[:8000]

		metadata: dict[str, Any] = {
			"url": url or "N/A",
			"domain": domain or "N/A",
			"lesson": fix_summary[:2000],
			"error": original_error[:2000],
			"timestamp": datetime.utcnow().isoformat(),
			"source": "auto_fix",
		}

		try:
			self.collection.add(
				documents=[doc_text],
				metadatas=[metadata],
				ids=[str(uuid.uuid4())],
			)
			logger.info("KnowledgeBaseService: Saved lesson to qa_insights.")
		except Exception as e:
			logger.error(f"KnowledgeBaseService: Failed to save lesson: {e}", exc_info=True)

	def recall_lessons(self, query: str, url: str | None = None, n_results: int = 3) -> str:
		"""Fetch relevant lessons for the current task.

		Returns a formatted context block or an empty string.
		"""
		if not self.collection:
			return ""

		query = (query or "").strip()
		if not query:
			return ""

		where = None
		domain = _extract_domain(url)
		# Optional filter by domain (helps avoid cross-project pollution).
		if domain:
			where = {"domain": domain}

		try:
			results = self.collection.query(
				query_texts=[query],
				n_results=n_results,
				include=["metadatas"],
				where=where,
			)
		except TypeError:
			# Older Chroma versions may not accept `where` or `include` in server mode.
			results = self.collection.query(query_texts=[query], n_results=n_results)
		except Exception as e:
			logger.error(f"KnowledgeBaseService: Query failed: {e}", exc_info=True)
			return ""

		metas = (results.get("metadatas") or [[]])[0]
		lessons: list[str] = []
		for meta in metas:
			if not isinstance(meta, dict):
				continue
			lesson = (meta.get("lesson") or "").strip()
			if lesson:
				lessons.append(f"- {lesson}")

		if not lessons:
			return ""

		return "\n\n[KNOWN PROJECT QUIRKS / MEMORY]:\n" + "\n".join(lessons)
