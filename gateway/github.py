import httpx


def get_user_ids(org_name):
    """
    Return a list of IDs of users belonging to the given GitHub organization.

    Note that GitHub IDs are numeric and fixed, unlike usernames which can change.
    """
    url = f"https://api.github.com/orgs/{org_name}/members"
    rsp = httpx.get(url)
    rsp.raise_for_status()
    return [user["id"] for user in rsp.json()]


def get_repo_names(org_name):
    """
    Return a list of repo names belonging to the given GitHub org.
    """
    url = f"https://api.github.com/orgs/{org_name}/repos"
    rsp = httpx.get(url)
    rsp.raise_for_status()
    return [repo["name"] for repo in rsp.json()]


def get_latest_commit(org_name, repo_name):
    """
    Return the SHA of the latest commit on the main branch of the given repo.
    """
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/commits"
    rsp = httpx.get(url, params={"sha": "main"})
    rsp.raise_for_status()
    return rsp.json()[0]["sha"]
