import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.app.services.gitlab import GitLabService
from src.app.services.deduplication import DeduplicationService

@pytest.mark.asyncio
@patch("src.app.services.gitlab.httpx.AsyncClient")
async def test_gitlab_create_mr(mock_client_cls: MagicMock) -> None:
    """Test MR creation logic with mocked httpx."""
    mock_client = AsyncMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    success_resp = MagicMock()
    success_resp.status_code = 201
    success_resp.json.return_value = {"web_url": "http://mr-url"}
    
    mock_client.post.side_effect = [success_resp, success_resp, success_resp]
    
    service = GitLabService(token="test")
    result = await service.create_mr("123", "code", "title")
    
    assert result["mr_url"] == "http://mr-url"
    assert mock_client.post.call_count == 3

@patch("src.app.services.deduplication.chromadb.PersistentClient")
def test_deduplication_find_similar(mock_chroma: MagicMock) -> None:
    """Test vector search logic."""
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    
    mock_collection.query.return_value = {
        "documents": [["def cached_test(): pass"]],
        "distances": [[0.1]]
    }
    
    service = DeduplicationService()
    result = service.find_similar("login test")
    
    assert result == "def cached_test(): pass"

@patch("src.app.services.deduplication.chromadb.PersistentClient")
def test_deduplication_no_match(mock_chroma: MagicMock) -> None:
    """Test when no similar test is found."""
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    
    mock_collection.query.return_value = {
        "documents": [["irrelevant code"]],
        "distances": [[0.9]]
    }
    
    service = DeduplicationService()
    result = service.find_similar("login test", threshold=0.2)
    
    assert result is None
