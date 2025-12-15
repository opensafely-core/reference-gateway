from urllib.parse import parse_qs, urlparse

from .helpers import mocked_responses


def test_index(client):
    rsp = client.get("/")
    assert rsp.status_code == 200


def test_login(client, settings):
    settings.GITHUB_OAUTH_CLIENT_ID = "client-id"
    rsp = client.get("/auth/login/")
    assert rsp.status_code == 302
    location = rsp["Location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    assert params["client_id"][0] == "client-id"
    assert params["allow_signup"][0] == "false"
    assert params["scope"][0] == "read:user"
    assert params["state"][0] == client.session["github_oauth_state"]
    assert params["redirect_uri"][0] == "http://testserver/auth/login/callback/"


def test_login_callback_logs_user_in(client, settings, user):
    settings.GITHUB_OAUTH_CLIENT_ID = "client-id"
    settings.GITHUB_OAUTH_CLIENT_SECRET = "client-secret"
    session = client.session
    session["github_oauth_state"] = "expected-state"
    session.save()

    with mocked_responses(
        post_data={"access_token": "token"},
        get_data={"id": user.profile.github_id},
    ):
        rsp = client.get(
            "/auth/login/callback/",
            {"code": "abcd", "state": "expected-state"},
        )

    assert rsp.status_code == 302
    assert rsp["Location"] == "/"
    assert client.session["_auth_user_id"] == str(user.id)


def test_login_callback_rejects_unknown_user(client, settings, user):
    settings.GITHUB_OAUTH_CLIENT_ID = "client-id"
    settings.GITHUB_OAUTH_CLIENT_SECRET = "client-secret"
    session = client.session
    session["github_oauth_state"] = "expected-state"
    session.save()

    with mocked_responses(
        post_data={"access_token": "token"},
        get_data={"id": 999},
    ):
        rsp = client.get(
            "/auth/login/callback/",
            {"code": "abcd", "state": "expected-state"},
        )

    assert rsp.status_code == 403
    assert "_auth_user_id" not in client.session


def test_login_callback_rejects_inactive_user(client, settings, user):
    user.is_active = False
    user.save()

    settings.GITHUB_OAUTH_CLIENT_ID = "client-id"
    settings.GITHUB_OAUTH_CLIENT_SECRET = "client-secret"
    session = client.session
    session["github_oauth_state"] = "expected-state"
    session.save()

    with mocked_responses(
        post_data={"access_token": "token"},
        get_data={"id": user.profile.github_id},
    ):
        rsp = client.get(
            "/auth/login/callback/",
            {"code": "abcd", "state": "expected-state"},
        )

    assert rsp.status_code == 403
    assert "_auth_user_id" not in client.session


def test_login_callback_rejects_bad_request(client, settings):
    session = client.session
    session["github_oauth_state"] = "expected-state"
    session.save()

    for data in [
        # missing state
        {"code": "abcd"},
        # incorrect state
        {"code": "abcd", "state": "different-state"},
        # missing code
        {"state": "expected-state"},
    ]:
        rsp = client.get("/auth/login/callback/", data)
        assert rsp.status_code == 400


def test_logout_logs_user_out(client, user):
    client.force_login(user)
    rsp = client.post("/auth/logout/")
    assert rsp.status_code == 302
    assert rsp["Location"] == "/"
    assert "_auth_user_id" not in client.session


def test_logout_rejects_get(client, user):
    client.force_login(user)
    rsp = client.get("/auth/logout/")
    assert rsp.status_code == 405
