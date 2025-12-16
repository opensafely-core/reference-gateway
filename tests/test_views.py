from urllib.parse import parse_qs, urlparse

from .helpers import mocked_responses


def test_get_projects(client, project):
    rsp = client.get("/")
    assert rsp.status_code == 200
    assert project.name in rsp.content.decode()


def test_get_project_with_no_current_run_not_logged_in(
    client, project_with_no_current_run
):
    rsp = client.get(f"/projects/{project_with_no_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" not in rsp.content.decode()


def test_get_project_with_no_current_run_logged_in(
    client, project_with_no_current_run, user
):
    client.force_login(user)
    rsp = client.get(f"/projects/{project_with_no_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" in rsp.content.decode()


def test_get_project_with_current_run_not_logged_in(client, project_with_current_run):
    rsp = client.get(f"/projects/{project_with_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" not in rsp.content.decode()


def test_get_project_with_current_run_logged_in(client, project_with_current_run, user):
    client.force_login(user)
    rsp = client.get(f"/projects/{project_with_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" not in rsp.content.decode()


def test_post_project_not_logged_in(client, project_with_no_current_run):
    with mocked_responses():
        rsp = client.post(f"/projects/{project_with_no_current_run.name}/")
    assert rsp.status_code == 403


def test_post_project_logged_in(monkeypatch, client, project_with_no_current_run, user):
    rap_id = "abcd1234efgh5678"
    commit_sha = "commit-sha"
    github_data = [
        {
            "sha": commit_sha,
            "commit": {"message": "Example commit"},
        }
    ]
    rap_api_data = {
        "result": "Success",
        "details": f"Jobs created for rap_id '{rap_id}'",
        "rap_id": rap_id,
        "count": 2,
    }

    monkeypatch.setattr("gateway.actions._generate_rap_id", lambda: rap_id)

    client.force_login(user)

    with mocked_responses(
        get_data=github_data,
        post_data=rap_api_data,
    ):
        rsp = client.post(f"/projects/{project_with_no_current_run.name}/")

    assert rsp.status_code == 302
    assert rsp["Location"] == "/runs/abcd1234efgh5678/"


def test_get_current_run_not_logged_in(client, current_run):
    with mocked_responses(post_data={"jobs": []}):
        rsp = client.get(f"/runs/{current_run.id}/")
    assert rsp.status_code == 200
    assert "Cancel run" not in rsp.content.decode()


def test_get_current_run_logged_in(client, current_run, user):
    client.force_login(user)
    with mocked_responses(post_data={"jobs": []}):
        rsp = client.get(f"/runs/{current_run.id}/")
    assert rsp.status_code == 200
    assert "Cancel run" in rsp.content.decode()


def test_get_successful_run_not_logged_in(client, successful_run):
    with mocked_responses():
        rsp = client.get(f"/runs/{successful_run.id}/")
    assert rsp.status_code == 200
    assert "Cancel run" not in rsp.content.decode()


def test_get_successful_run_logged_in(client, successful_run, user):
    client.force_login(user)
    with mocked_responses():
        rsp = client.get(f"/runs/{successful_run.id}/")
    assert rsp.status_code == 200
    assert "Cancel run" not in rsp.content.decode()


def test_post_current_run_not_logged_in(client, current_run):
    with mocked_responses():
        rsp = client.post(f"/runs/{current_run.id}/")
    assert rsp.status_code == 403


def test_post_current_run_logged_in(client, current_run, user):
    client.force_login(user)
    with mocked_responses():
        rsp = client.post(f"/runs/{current_run.id}/")
    assert rsp.status_code == 302
    assert rsp["Location"] == f"/runs/{current_run.id}/"


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
