import re

from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

from gateway.actions import (
    _create_or_update_jobs,
    _create_run,
    _generate_rap_id,
    cancel_run,
    create_or_update_projects,
    create_or_update_users,
    start_run,
    update_run,
)
from gateway.models import Job, Project, Run

from .helpers import mocked_responses


def test_create_or_update_projects():
    github_data_1 = [
        {"id": 123, "name": "test-1", "description": "Description"},
        {"id": 456, "name": "test-2", "description": "Description"},
    ]
    github_data_2 = [
        {"id": 123, "name": "updated-test-1", "description": "Updated description"},
        {"id": 789, "name": "test-3", "description": "Description"},
    ]

    with mocked_responses(get_data=github_data_1):
        create_or_update_projects()

    assert Project.objects.count() == 2

    p1 = Project.objects.get(pk=123)
    assert p1.name == "test-1"
    assert p1.description == "Description"

    p2 = Project.objects.get(pk=456)
    assert p2.name == "test-2"
    assert p2.description == "Description"

    with mocked_responses(get_data=github_data_2):
        create_or_update_projects()

    assert Project.objects.count() == 3

    p1 = Project.objects.get(pk=123)
    assert p1.name == "updated-test-1"
    assert p1.description == "Updated description"

    p2 = Project.objects.get(pk=456)
    assert p2.name == "test-2"
    assert p2.description == "Description"

    p3 = Project.objects.get(pk=789)
    assert p3.name == "test-3"
    assert p3.description == "Description"


def test_create_or_update_projects_ignores_invalid_slug_repos(caplog):
    github_data = [
        {"id": 123, "name": ".github", "description": "Ignored"},
        {"id": 124, "name": "my.repo", "description": "Ignored"},
        {"id": 456, "name": "test-2", "description": "Description"},
    ]

    with mocked_responses(get_data=github_data):
        create_or_update_projects()

    assert Project.objects.count() == 1
    assert not Project.objects.filter(name=".github").exists()
    assert not Project.objects.filter(name="my.repo").exists()
    assert "Ignoring GitHub repo with invalid slug name: .github" in caplog.text
    assert "Ignoring GitHub repo with invalid slug name: my.repo" in caplog.text

    project = Project.objects.get(pk=456)
    assert project.name == "test-2"
    assert project.description == "Description"


def test_create_or_update_users():
    User = get_user_model()
    github_data_1 = [
        {"id": 123, "login": "test-1"},
        {"id": 456, "login": "test-2"},
    ]
    github_data_2 = [
        {"id": 123, "login": "updated-test-1"},
        {"id": 789, "login": "test-3"},
    ]

    with mocked_responses(get_data=github_data_1):
        create_or_update_users()

    assert User.objects.count() == 2

    u1 = User.objects.get(github_id=123)
    assert u1.username == "test-1"
    assert u1.is_active

    u2 = User.objects.get(github_id=456)
    assert u2.username == "test-2"
    assert u2.is_active

    with mocked_responses(get_data=github_data_2):
        create_or_update_users()

    assert User.objects.count() == 3

    u1 = User.objects.get(github_id=123)
    assert u1.username == "updated-test-1"
    assert u1.is_active

    u2 = User.objects.get(github_id=456)
    assert u2.username == "test-2"
    assert not u2.is_active

    u3 = User.objects.get(github_id=789)
    assert u3.username == "test-3"
    assert u3.is_active


def test_start_run(project, user, monkeypatch):
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

    with mocked_responses(get_data=github_data, post_data=rap_api_data):
        run = start_run(project=project, user=user)

    assert run.id == rap_id
    assert run.project == project
    assert run.user == user
    assert run.state == Run.State.PENDING
    assert run.jobs.count() == 0


def test_update_run(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)

    t0 = "2025-12-05T19:07:40Z"
    t1 = "2025-12-05T19:08:40Z"
    t2 = "2025-12-05T19:09:40Z"

    rap_api_data_1 = {
        "jobs": [
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "generate_dataset",
                "status": "pending",
                "created_at": t0,
                "updated_at": t0,
                "started_at": None,
                "completed_at": None,
            },
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "bbbbbbbbbbbbbbbb",
                "action": "count_by_age",
                "status": "pending",
                "created_at": t0,
                "updated_at": t0,
                "started_at": None,
                "completed_at": None,
            },
        ],
        "unrecognised_rap_ids": [],
    }

    rap_api_data_2 = {
        "jobs": [
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "generate_dataset",
                "status": "succeeded",
                "created_at": t0,
                "updated_at": t2,
                "started_at": t1,
                "completed_at": t2,
            },
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "bbbbbbbbbbbbbbbb",
                "action": "count_by_age",
                "status": "running",
                "created_at": t0,
                "updated_at": t2,
                "started_at": t2,
                "completed_at": None,
            },
        ],
        "unrecognised_rap_ids": [],
    }

    with mocked_responses(post_data=rap_api_data_1):
        update_run(run=run)

    run.refresh_from_db()

    assert run.state == Run.State.PENDING
    assert run.jobs.count() == 2

    dataset_job = run.jobs.get(id="aaaaaaaaaaaaaaaa")
    assert dataset_job.action == "generate_dataset"
    assert dataset_job.state == Job.State.PENDING
    assert dataset_job.created_at == parse_datetime(t0)
    assert dataset_job.updated_at == parse_datetime(t0)
    assert dataset_job.started_at is None
    assert dataset_job.completed_at is None

    count_job = run.jobs.get(id="bbbbbbbbbbbbbbbb")
    assert count_job.action == "count_by_age"
    assert count_job.state == Job.State.PENDING
    assert count_job.created_at == parse_datetime(t0)
    assert count_job.updated_at == parse_datetime(t0)
    assert count_job.started_at is None
    assert count_job.completed_at is None

    with mocked_responses(post_data=rap_api_data_2):
        update_run(run=run)

    run.refresh_from_db()

    assert run.state == Run.State.RUNNING
    assert run.jobs.count() == 2

    dataset_job = run.jobs.get(id="aaaaaaaaaaaaaaaa")
    assert dataset_job.action == "generate_dataset"
    assert dataset_job.state == Job.State.SUCCEEDED
    assert dataset_job.created_at == parse_datetime(t0)
    assert dataset_job.updated_at == parse_datetime(t2)
    assert dataset_job.started_at == parse_datetime(t1)
    assert dataset_job.completed_at == parse_datetime(t2)

    count_job = run.jobs.get(id="bbbbbbbbbbbbbbbb")
    assert count_job.action == "count_by_age"
    assert count_job.state == Job.State.RUNNING
    assert count_job.created_at == parse_datetime(t0)
    assert count_job.updated_at == parse_datetime(t2)
    assert count_job.started_at == parse_datetime(t2)
    assert count_job.completed_at is None


def test_cancel_run(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(
        run=run,
        jobs_data=[
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "action1",
                "status": "pending",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": None,
                "started_at": None,
                "completed_at": None,
            },
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "bbbbbbbbbbbbbbbb",
                "action": "action2",
                "status": "pending",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": None,
                "started_at": None,
                "completed_at": None,
            },
        ],
    )

    with mocked_responses():
        cancel_run(run=run)
    assert run.state == Run.State.CANCELLED


def test_generate_rap_id():
    # This is the regex used in the createRequestBody validator in job-runner.
    assert re.match("^[a-z0-9]{16}$", _generate_rap_id())
