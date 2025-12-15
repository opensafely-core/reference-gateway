from contextlib import contextmanager
from unittest.mock import Mock, patch


@contextmanager
def mocked_responses(*, github_data=None, rap_api_data=None):
    github_httpx_rsp = Mock()
    github_httpx_rsp.json.return_value = github_data
    github_httpx_rsp.raise_for_status.return_value = None

    rap_api_httpx_rsp = Mock()
    rap_api_httpx_rsp.json.return_value = rap_api_data
    rap_api_httpx_rsp.raise_for_status.return_value = None

    with (
        patch("gateway.github.httpx.get", return_value=github_httpx_rsp),
        patch("gateway.rap_api.httpx.post", return_value=rap_api_httpx_rsp),
    ):
        yield
