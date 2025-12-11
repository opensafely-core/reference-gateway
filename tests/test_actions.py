import re
from contextlib import contextmanager
from unittest.mock import Mock, patch

from django.utils.dateparse import parse_datetime

from gateway.actions import (
    _create_or_update_jobs,
    _create_run,
    _generate_rap_id,
    cancel_run,
    start_run,
    update_run,
)
from gateway.models import Job, Run


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

    with mocked_responses(github_data=github_data, rap_api_data=rap_api_data):
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

    with mocked_responses(rap_api_data=rap_api_data_1):
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

    with mocked_responses(rap_api_data=rap_api_data_2):
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


@contextmanager
def mocked_responses(*, github_data=None, rap_api_data=None):
    github_httpx_rsp = Mock()
    github_httpx_rsp.json.return_value = github_data
    github_httpx_rsp.raise_for_status.return_value = None

    rap_api_httpx_rsp = Mock()
    rap_api_httpx_rsp.json.return_value = rap_api_data
    rap_api_httpx_rsp.raise_for_status.return_value = None

    with (
        patch("gateway.github.httpx.get", return_value=github_httpx_rsp),
        patch("gateway.rap_api.httpx.post", return_value=rap_api_httpx_rsp),
    ):
        yield
