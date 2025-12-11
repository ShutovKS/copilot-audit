import subprocess
from unittest.mock import patch

import pytest

from src.app.services.code_analysis.service import CodeAnalysisService


@patch("src.app.services.code_analysis.service.subprocess.run")
@patch("src.app.services.code_analysis.service.tempfile.TemporaryDirectory")
def test_clone_url_construction(mock_temp, mock_run):
    """Test that token is correctly injected into the URL."""
    service = CodeAnalysisService()
    mock_temp.return_value.__enter__.return_value = "/tmp/test"

    # Mock successful run
    mock_run.return_value.returncode = 0

    repo = "https://github.com/my/repo.git"
    token = "secret123"

    service.clone_and_analyze(repo, token)

    # Verify the URL passed to git clone contains the token
    args = mock_run.call_args[0][0]
    expected_url = "https://oauth2:secret123@github.com/my/repo.git"
    assert expected_url in args

@patch("src.app.services.code_analysis.service.logger")
@patch("src.app.services.code_analysis.service.subprocess.run")
def test_token_masking_in_logs(mock_run, mock_logger):
    """Test that we do not log the token even if git fails."""
    service = CodeAnalysisService()

    repo = "https://github.com/my/repo.git"
    token = "SUPER_SECRET_TOKEN"

    # Simulate Git Failure that includes the URL in stderr
    error_msg = f"fatal: unable to access 'https://oauth2:{token}@github.com/my/repo.git': The requested URL returned error: 403"
    mock_run.side_effect = subprocess.CalledProcessError(128, cmd="git clone", stderr=error_msg.encode('utf-8'))

    with pytest.raises(Exception) as exc_info:
        service.clone_and_analyze(repo, token)

    # Check that exception message is masked
    assert "***TOKEN***" in str(exc_info.value)
    assert token not in str(exc_info.value)

    # Check that logger error is masked
    log_call = mock_logger.error.call_args[0][0]
    assert "***TOKEN***" in log_call
    assert token not in log_call
