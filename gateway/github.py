import httpx
from django.conf import settings


TIMEOUT = 10


def get_user_metadata(org_name):
    """
    Return a list of metadata about users belonging to the given GitHub org.
    """
    data = get_json(f"/orgs/{org_name}/members")
    return [pluck(user, ["id", "login"]) for user in data]


def get_repo_metadata(org_name):
    """
    Return a list of metadata about repos belonging to the given GitHub org.
    """
    data = get_json(f"/orgs/{org_name}/repos")
    return [pluck(user, ["id", "name", "description"]) for user in data]


def get_latest_commit(org_name, repo_name):
    """
    Return the SHA of the latest commit on the main branch of the given repo.
    """
    data = get_json(f"/{org_name}/{repo_name}/commits", {"sha": "main"})
    return data[0]["sha"]


def get_user_for_token(token):
    return get_json("/user", token=token)


def exchange_code_for_token(code):
    rsp = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    rsp.raise_for_status()
    return rsp.json()["access_token"]


def get_json(path, params=None, token=None):
    assert path[0] == "/"
    token = token or settings.GITHUB_TOKEN
    rsp = httpx.get(
        f"https://api.github.com{path}",
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    rsp.raise_for_status()
    return rsp.json()


def pluck(d, keys):
    """
    Return a new dictionary with the given keys.

    The name comes from the similar builtin method in Ruby.
    """
    return {k: d[k] for k in keys}
