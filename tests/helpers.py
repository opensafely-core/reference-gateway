from contextlib import contextmanager
from unittest.mock import Mock, patch


@contextmanager
def mocked_responses(*, get_data=None, post_data=None):
    get_rsp = Mock()
    get_rsp.json.return_value = get_data
    get_rsp.raise_for_status.return_value = None

    post_rsp = Mock()
    post_rsp.json.return_value = post_data
    post_rsp.raise_for_status.return_value = None

    with (
        patch("httpx.get", return_value=get_rsp),
        patch("httpx.post", return_value=post_rsp),
    ):
        yield
