import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from gateway.login_tokens import generate_login_token
from gateway.models import Project


@pytest.fixture
def client():
    return Client()


def _backend_headers(token):
    return {"HTTP_AUTHORIZATION": token}


def _post_json(client, url, data, *, token):
    return client.post(
        url,
        json.dumps(data),
        content_type="application/json",
        **_backend_headers(token),
    )


def _assert_valid_level4_response(data, user, projects):
    assert data["username"] == user.username
    assert data["fullname"] == (user.get_full_name() or user.username)
    assert data["copiloted_workspaces"] == {}
    assert data["output_checker"] is False
    expected_workspaces = {
        p.name: {
            "project_details": {"name": p.name, "ongoing": True, "orgs": []},
            "archived": False,
        }
        for p in sorted(projects, key=lambda p: p.name)
    }
    assert data["workspaces"] == expected_workspaces


def _generate_api_login_token(user):
    return generate_login_token(user=user)


def test_authenticate_returns_200_by_username(client, settings, user, project):
    login_token = _generate_api_login_token(user)
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "alice", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), user, [project])


@pytest.mark.parametrize(
    "method,body,expected_status",
    [
        ("POST", '{"user": "nobody", "token": "x"}', 401),
        ("POST", '{"token": "x"}', 400),
        ("POST", '{"user": "alice"}', 400),
        ("POST", "not json", 400),
        ("GET", None, 405),
    ],
    ids=[
        "unknown_user",
        "missing_user",
        "missing_token",
        "invalid_json",
        "get_not_allowed",
    ],
)
def test_authenticate_errors(client, settings, method, body, expected_status):
    if method == "GET":
        response = client.get("/api/v2/releases/authenticate")
    else:
        response = client.post(
            "/api/v2/releases/authenticate",
            body,
            content_type="application/json",
            **_backend_headers(settings.AIRLOCK_TOKEN),
        )
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "header_value,expected_detail",
    [
        (None, "Authorization header is missing"),
        ("", "Authorization header is empty"),
        ("wrong-token", "Invalid token"),
    ],
    ids=["missing_header", "empty_header", "invalid_token"],
)
def test_authenticate_backend_authentication_errors(
    client, settings, header_value, expected_detail
):
    kwargs = {}
    if header_value is not None:
        kwargs.update(_backend_headers(header_value))
    response = client.post(
        "/api/v2/releases/authenticate",
        json.dumps({"user": "alice", "token": "x"}),
        content_type="application/json",
        **kwargs,
    )
    assert response.status_code == 401
    assert response.json() == {"detail": expected_detail}


def test_authenticate_workspaces_contain_all_projects(client, settings, user):
    alpha = Project.objects.create(id=1, name="alpha", description="Alpha")
    beta = Project.objects.create(id=2, name="beta", description="Beta")
    login_token = _generate_api_login_token(user)
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "alice", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), user, [alpha, beta])


def test_authenticate_fullname_falls_back_to_username(client, settings):
    User = get_user_model()
    noname = User.objects.create_user(username="noname", github_id=789)
    login_token = _generate_api_login_token(noname)
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "noname", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), noname, [])


def test_authenticate_fullname_uses_full_name_when_set(client, settings):
    User = get_user_model()
    fulluser = User.objects.create_user(username="fulluser", github_id=790)
    fulluser.full_name = "Full User"
    fulluser.save(update_fields=["full_name"])
    login_token = _generate_api_login_token(fulluser)
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "fulluser", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), fulluser, [])


def test_authenticate_rejects_invalid_login_token(client, settings, user):
    _generate_api_login_token(user)
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "alice", "token": "wrong-token"},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 401


def test_authenticate_consumes_login_token(client, settings, user):
    login_token = _generate_api_login_token(user)

    first_response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "alice", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )
    second_response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "alice", "token": login_token},
        token=settings.AIRLOCK_TOKEN,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 401


def test_authorise_returns_200_by_username(client, settings, user, project):
    response = _post_json(
        client,
        "/api/v2/releases/authorise",
        {"user": "alice"},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), user, [project])


@pytest.mark.parametrize(
    "method,body,expected_status",
    [
        ("POST", '{"user": "nobody"}', 404),
        ("POST", "{}", 400),
        ("POST", "not json", 400),
        ("GET", None, 405),
    ],
    ids=["unknown_user", "missing_user", "invalid_json", "get_not_allowed"],
)
def test_authorise_errors(client, settings, method, body, expected_status):
    if method == "GET":
        response = client.get("/api/v2/releases/authorise")
    else:
        response = client.post(
            "/api/v2/releases/authorise",
            body,
            content_type="application/json",
            **_backend_headers(settings.AIRLOCK_TOKEN),
        )
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "header_value,expected_detail",
    [
        (None, "Authorization header is missing"),
        ("", "Authorization header is empty"),
        ("wrong-token", "Invalid token"),
    ],
    ids=["missing_header", "empty_header", "invalid_token"],
)
def test_authorise_backend_authentication_errors(
    client, settings, header_value, expected_detail
):
    kwargs = {}
    if header_value is not None:
        kwargs.update(_backend_headers(header_value))
    response = client.post(
        "/api/v2/releases/authorise",
        json.dumps({"user": "alice"}),
        content_type="application/json",
        **kwargs,
    )
    assert response.status_code == 401
    assert response.json() == {"detail": expected_detail}


def test_authorise_does_not_look_up_by_email(client, settings):
    User = get_user_model()
    User.objects.create_user(username="carol", email="carol@example.com")
    response = _post_json(
        client,
        "/api/v2/releases/authorise",
        {"user": "carol@example.com"},
        token=settings.AIRLOCK_TOKEN,
    )
    assert response.status_code == 404
