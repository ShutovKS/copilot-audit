from unittest.mock import MagicMock, patch

from src.app.services.memory import KnowledgeBaseService


@patch("src.app.services.memory.chromadb.HttpClient")
def test_memory_learn_lesson_saves_to_collection(mock_chroma: MagicMock) -> None:
	mock_collection = MagicMock()
	mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

	service = KnowledgeBaseService()
	service.learn_lesson(
		url="https://site.example/path",
		original_error="Element not interactable",
		fix_summary="Login button is covered; use force click.",
	)

	assert mock_collection.add.call_count == 1
	kwargs = mock_collection.add.call_args.kwargs
	assert "documents" in kwargs
	assert "metadatas" in kwargs
	meta = kwargs["metadatas"][0]
	assert meta["url"] == "https://site.example/path"
	assert meta["domain"] == "site.example"
	assert "lesson" in meta and "force click" in meta["lesson"]


@patch("src.app.services.memory.chromadb.HttpClient")
def test_memory_recall_lessons_formats_context(mock_chroma: MagicMock) -> None:
	mock_collection = MagicMock()
	mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

	mock_collection.query.return_value = {
		"ids": [["id1", "id2"]],
		"metadatas": [[
			{"lesson": "Use data-testid for login button"},
			{"lesson": "Add wait_for_load_state('networkidle') after redirect"},
		]],
	}

	service = KnowledgeBaseService()
	ctx = service.recall_lessons("login test", url="https://site.example/login")

	assert "[KNOWN PROJECT QUIRKS / MEMORY]" in ctx
	assert "Use data-testid" in ctx
	assert "networkidle" in ctx


@patch("src.app.services.memory.chromadb.HttpClient")
def test_memory_recall_lessons_empty_when_no_results(mock_chroma: MagicMock) -> None:
	mock_collection = MagicMock()
	mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

	mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]]}

	service = KnowledgeBaseService()
	ctx = service.recall_lessons("something")
	assert ctx == ""
