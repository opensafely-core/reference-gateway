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


def get_json(path, params=None):
    assert path[0] == "/"
    rsp = httpx.get(
        f"https://api.github.com{path}",
        params=params,
        headers={
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
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
