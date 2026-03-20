import pytest
from django.contrib.auth import get_user_model

from gateway.actions import _create_or_update_jobs, _create_run
from gateway.models import Project


@pytest.fixture(autouse=True)
def enable_db_for_all_tests(db):
    yield


@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(username="alice", github_id=123)


@pytest.fixture
def project():
    return Project.objects.create(id=123, name="example", description="Example project")


@pytest.fixture
def project_with_no_current_run(project):
    # Even though this returns another fixture unchanged, it's sometimes helpful to use
    # a more precise name.
    return project


@pytest.fixture
def project_with_current_run(user):
    project = Project.objects.create(
        id=456, name="another-example", description="Another example project"
    )
    run = _create_run(rap_id="abc123def456gh", project=project, user=user)
    _create_or_update_jobs(
        run=run,
        jobs_data=[
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "action",
                "status": "pending",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": None,
                "started_at": None,
                "completed_at": None,
            },
        ],
    )
    return project


@pytest.fixture
def run(project_with_current_run):
    return project_with_current_run.runs.get()


@pytest.fixture
def current_run(run):
    # Even though this returns another fixture unchanged, it's sometimes helpful to use
    # a more precise name.
    return run


@pytest.fixture
def successful_run(run):
    _create_or_update_jobs(
        run=run,
        jobs_data=[
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "action",
                "status": "succeeded",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": "2025-12-05T19:09:40Z",
                "started_at": "2025-12-05T19:08:40Z",
                "completed_at": "2025-12-05T19:09:40Z",
            },
        ],
    )
    return run
