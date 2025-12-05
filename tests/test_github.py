from contextlib import contextmanager
from unittest.mock import Mock, patch

from gateway import github


def test_get_user_ids():
    data = [
        {"id": 123, "login": "user1"},
        {"id": 456, "login": "user2"},
        {"id": 789, "login": "user3"},
    ]
    with mocked_response(data):
        result = github.get_user_ids("test-org")
    assert result == [123, 456, 789]


def test_get_repo_names():
    data = [
        {"id": 123, "name": "repo1"},
        {"id": 456, "name": "repo2"},
        {"id": 789, "name": "repo3"},
    ]
    with mocked_response(data):
        result = github.get_repo_names("test-org")
    assert result == ["repo1", "repo2", "repo3"]


def test_get_latest_commit():
    data = [
        {"sha": "abc123def456", "commit": {"message": "Fix typo"}},
        {"sha": "cba321fed654", "commit": {"message": "Initial commit"}},
    ]
    with mocked_response(data):
        result = github.get_latest_commit("test-org", "test-repo")
    assert result == "abc123def456"


@contextmanager
def mocked_response(data):
    mock_response = Mock()
    mock_response.json.return_value = data
    with patch("gateway.github.httpx.get", return_value=mock_response):
        yield
