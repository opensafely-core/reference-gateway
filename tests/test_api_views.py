import json

import pytest
from django.contrib.auth.models import User
from django.test import Client

from gateway.models import Project


@pytest.fixture
def client():
    return Client()


def _post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type="application/json")


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


def test_authenticate_returns_200_by_username(client, user, project):
    response = _post_json(
        client, "/api/v2/releases/authenticate", {"user": "alice", "token": "x"}
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), user, [project])


def test_authenticate_returns_200_by_email(client, project):
    bob = User.objects.create_user(username="bob", email="bob@example.com")
    response = _post_json(
        client,
        "/api/v2/releases/authenticate",
        {"user": "bob@example.com", "token": "x"},
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), bob, [project])


@pytest.mark.parametrize(
    "method,body,expected_status",
    [
        ("POST", '{"user": "nobody", "token": "x"}', 404),
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
def test_authenticate_errors(client, method, body, expected_status):
    if method == "GET":
        response = client.get("/api/v2/releases/authenticate")
    else:
        response = client.post(
            "/api/v2/releases/authenticate", body, content_type="application/json"
        )
    assert response.status_code == expected_status


def test_authenticate_workspaces_contain_all_projects(client, user):
    alpha = Project.objects.create(id=1, name="alpha", description="Alpha")
    beta = Project.objects.create(id=2, name="beta", description="Beta")
    response = _post_json(
        client, "/api/v2/releases/authenticate", {"user": "alice", "token": "x"}
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), user, [alpha, beta])


def test_authenticate_fullname_falls_back_to_username(client):
    noname = User.objects.create_user(username="noname")
    response = _post_json(
        client, "/api/v2/releases/authenticate", {"user": "noname", "token": "x"}
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), noname, [])


def test_authenticate_fullname_uses_full_name_when_set(client):
    fulluser = User.objects.create_user(
        username="fulluser", first_name="Full", last_name="User"
    )
    response = _post_json(
        client, "/api/v2/releases/authenticate", {"user": "fulluser", "token": "x"}
    )
    assert response.status_code == 200
    _assert_valid_level4_response(response.json(), fulluser, [])


def test_authorise_returns_200_by_username(client, user, project):
    response = _post_json(client, "/api/v2/releases/authorise", {"user": "alice"})
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
def test_authorise_errors(client, method, body, expected_status):
    if method == "GET":
        response = client.get("/api/v2/releases/authorise")
    else:
        response = client.post(
            "/api/v2/releases/authorise", body, content_type="application/json"
        )
    assert response.status_code == expected_status


def test_authorise_does_not_look_up_by_email(client):
    User.objects.create_user(username="carol", email="carol@example.com")
    response = _post_json(
        client, "/api/v2/releases/authorise", {"user": "carol@example.com"}
    )
    assert response.status_code == 404
