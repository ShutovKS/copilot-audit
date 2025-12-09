import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from src.app.main import app

client = TestClient(app)

async def mock_astream_generator(*args, **kwargs):
    yield {"analyst": {"logs": ["Analyzing request..."]}}
    yield {"coder": {"logs": ["Writing code..."], "generated_code": "def test(): pass"}}
    yield {"reviewer": {"status": "COMPLETED"}}

@pytest.fixture
def mock_app_graph():
    mock_graph = MagicMock()
    mock_graph.astream.side_effect = mock_astream_generator
    app.state.agent_graph = mock_graph
    return mock_graph

def test_generate_endpoint(mock_app_graph) -> None:
    """Test the SSE generation endpoint."""
    payload = {"user_request": "Create a test for calculator"}
    
    with patch("src.app.api.endpoints.generation.HistoryService") as MockHistory:
        mock_history_instance = AsyncMock()
        mock_history_instance.create_run.return_value.id = 1
        MockHistory.return_value = mock_history_instance
        
        response = client.post(
            "/api/v1/generate", 
            json=payload, 
            headers={"X-Session-ID": "test-session-uuid"}
        )
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    content = response.text
    assert "Analyzing request..." in content
    assert "def test(): pass" in content
    assert "COMPLETED" in content

@patch("src.app.services.gitlab.GitLabService.create_mr")
def test_export_gitlab_success(mock_create_mr: AsyncMock) -> None:
    """Test successful GitLab export."""
    mock_create_mr.return_value = {
        "status": "success",
        "mr_url": "https://gitlab.com/repo/mr/1",
        "branch": "feature/test-1"
    }
    
    payload = {
        "code": "print('hello')",
        "project_id": "123",
        "token": "glpat-secret",
        "url": "https://gitlab.com",
        "title": "Test MR"
    }
    
    response = client.post("/api/v1/export/gitlab", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["mr_url"] == "https://gitlab.com/repo/mr/1"

@patch("src.app.services.gitlab.GitLabService.create_mr")
def test_export_gitlab_failure(mock_create_mr: AsyncMock) -> None:
    """Test GitLab export handling errors."""
    mock_create_mr.side_effect = Exception("GitLab API Down")
    
    payload = {
        "code": "print('hello')",
        "project_id": "123",
        "token": "glpat-secret"
    }
    
    response = client.post("/api/v1/export/gitlab", json=payload)
    
    assert response.status_code == 400
    assert "GitLab API Down" in response.json()["detail"]
