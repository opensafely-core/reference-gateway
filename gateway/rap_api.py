import httpx
from django.conf import settings


TIMEOUT = 10


def create(*, rap_id, project, commit, username):
    payload = {
        "rap_id": rap_id,
        "backend": settings.OPENSAFELY_BACKEND,
        "project": project,
        # In the original OpenSAFELY implementation, a project has many workspaces.
        # This implementation does not use workspaces, so we reuse the project name.
        "workspace": project,
        "repo_url": f"https://github.com/{settings.GITHUB_ORG}/{project}",
        "branch": "main",
        "commit": commit,
        "created_by": username,
        # We always want to run all the actions in a project.yaml.
        "requested_actions": ["run_all"],
        "force_run_dependencies": True,
        # These are parameters that we don't need to use, but which are required by v1
        # of the RAP API.
        "orgs": [],
        "database_name": "default",
        "codelists_ok": True,
    }
    return post_json("/rap/create/", payload)


def cancel(rap_id, actions):
    payload = {
        "rap_id": rap_id,
        "actions": actions,
    }
    return post_json("/rap/cancel/", payload)


def status(rap_ids):
    payload = {"rap_ids": rap_ids}
    return post_json("/rap/status/", payload)


def post_json(path, payload):
    assert path[0] == "/"
    rsp = httpx.post(
        f"{settings.RAP_CONTROLLER_URL}{path}",
        json=payload,
        timeout=TIMEOUT,
        headers={
            "Authorization": settings.RAP_CONTROLLER_TOKEN,
            "Accept": "application/json",
        },
    )
    rsp.raise_for_status()
    return rsp.json()
