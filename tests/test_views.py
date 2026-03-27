from urllib.parse import parse_qs, urlparse

from django.contrib.auth.hashers import check_password

from .helpers import mocked_responses


def test_get_projects(client, project):
    rsp = client.get("/")
    assert rsp.status_code == 200
    assert project.name in rsp.content.decode()


def test_healthz(client):
    rsp = client.get("/healthz/")
    assert rsp.status_code == 200
    assert rsp.content.decode() == "ok"


def test_get_project_with_no_current_run_not_logged_in(
    client, project_with_no_current_run
):
    rsp = client.get(f"/projects/{project_with_no_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" not in rsp.content.decode()


def test_get_project_with_no_current_run_logged_in(
    client, project_with_no_current_run, user
):
    user.full_name = "Alice Example"
    user.save(update_fields=["full_name"])
    client.force_login(user)
    rsp = client.get(f"/projects/{project_with_no_current_run.name}/")
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert "Run Now" in body
    assert "Signed in as <strong>Alice Example</strong>" in body


def test_get_project_with_current_run_not_logged_in(client, project_with_current_run):
    rsp = client.get(f"/projects/{project_with_current_run.name}/")
    assert rsp.status_code == 200
    assert "Run Now" not in rsp.content.decode()


def test_get_project_with_current_run_logged_in(client, project_with_current_run, user):
    user.full_name = "Alice Example"
    user.save(update_fields=["full_name"])
    client.force_login(user)
    rsp = client.get(f"/projects/{project_with_current_run.name}/")
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert "Run Now" not in body
    assert "Alice Example" in body


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
    user.full_name = "Alice Example"
    user.save(update_fields=["full_name"])
    client.force_login(user)
    with mocked_responses(post_data={"jobs": []}):
        rsp = client.get(f"/runs/{current_run.id}/")
    assert rsp.status_code == 200
    body = rsp.content.decode()
    assert "Cancel run" in body
    assert "Requested by Alice Example" in body


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


def test_ui_display_name_falls_back_to_username_when_full_name_missing(
    client, current_run, user
):
    client.force_login(user)
    with mocked_responses(post_data={"jobs": []}):
        rsp = client.get(f"/runs/{current_run.id}/")

    assert rsp.status_code == 200
    assert "Requested by alice" in rsp.content.decode()


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
        get_data={
            "id": user.github_id,
            "login": "alice-updated",
            "name": "Alice Example",
        },
    ):
        rsp = client.get(
            "/auth/login/callback/",
            {"code": "abcd", "state": "expected-state"},
        )

    assert rsp.status_code == 302
    assert rsp["Location"] == "/"
    assert client.session["_auth_user_id"] == str(user.id)
    user.refresh_from_db()
    assert user.username == "alice-updated"
    assert user.full_name == "Alice Example"


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
        get_data={"id": user.github_id, "login": user.username},
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


def test_login_callback_keeps_existing_name_when_github_omits_it(
    client, settings, user
):
    user.full_name = "Existing Name"
    user.save(update_fields=["full_name"])

    settings.GITHUB_OAUTH_CLIENT_ID = "client-id"
    settings.GITHUB_OAUTH_CLIENT_SECRET = "client-secret"
    session = client.session
    session["github_oauth_state"] = "expected-state"
    session.save()

    with mocked_responses(
        post_data={"access_token": "token"},
        get_data={
            "id": user.github_id,
            "login": "alice-renamed",
            "name": "",
        },
    ):
        rsp = client.get(
            "/auth/login/callback/",
            {"code": "abcd", "state": "expected-state"},
        )

    assert rsp.status_code == 302
    user.refresh_from_db()
    assert user.username == "alice-renamed"
    assert user.full_name == "Existing Name"


def test_airlock_token_requires_login(client):
    rsp = client.get("/auth/airlock-token/")
    assert rsp.status_code == 302
    assert rsp["Location"].startswith("/accounts/login/")


def test_airlock_token_page_is_linked_for_logged_in_user(client, user):
    client.force_login(user)
    rsp = client.get("/")
    assert rsp.status_code == 200
    assert 'href="/auth/airlock-token/"' in rsp.content.decode()


def test_airlock_token_get_renders_page_for_logged_in_user(client, user):
    client.force_login(user)
    rsp = client.get("/auth/airlock-token/")

    assert rsp.status_code == 200
    assert "Single-use login token" in rsp.content.decode()


def test_airlock_token_generates_token(client, user):
    client.force_login(user)
    rsp = client.post("/auth/airlock-token/")

    assert rsp.status_code == 200
    user.refresh_from_db()
    body = rsp.content.decode()
    assert "Single-use login token" in body
    assert user.login_token
    assert user.login_token_expires_at is not None
    assert check_password(
        "".join(body.split("<code>")[1].split("</code>")[0].split()), user.login_token
    )


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
