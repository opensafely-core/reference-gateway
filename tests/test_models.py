from gateway.actions import _create_or_update_jobs, _create_run, _mark_run_cancelled
from gateway.models import Run


def test_run_actions(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(
        run=run,
        jobs_data=[
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "aaaaaaaaaaaaaaaa",
                "action": "generate_dataset",
                "status": "pending",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": None,
                "started_at": None,
                "completed_at": None,
            },
            {
                "rap_id": "abcd1234efgh5678",
                "identifier": "bbbbbbbbbbbbbbbb",
                "action": "count_by_age",
                "status": "pending",
                "created_at": "2025-12-05T19:07:40Z",
                "updated_at": None,
                "started_at": None,
                "completed_at": None,
            },
        ],
    )
    assert run.actions == {"generate_dataset", "count_by_age"}


def test_run_state_no_jobs_yet(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    assert run.state == Run.State.PENDING


def test_run_state_all_jobs_pending(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(run=run, jobs_data=_build_job_data("pending", "pending"))
    assert run.state == Run.State.PENDING


def test_run_state_some_jobs_running(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(run=run, jobs_data=_build_job_data("running", "pending"))
    assert run.state == Run.State.RUNNING


def test_run_state_all_jobs_succeeded(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(run=run, jobs_data=_build_job_data("succeeded", "succeeded"))
    assert run.state == Run.State.SUCCEEDED


def test_run_state_one_job_failed(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(run=run, jobs_data=_build_job_data("succeeded", "failed"))
    assert run.state == Run.State.FAILED


def test_run_state_cancelled(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    _create_or_update_jobs(run=run, jobs_data=_build_job_data("running", "pending"))
    _mark_run_cancelled(run=run)
    assert run.state == Run.State.CANCELLED


def _build_job_data(*states):
    return [
        {
            "rap_id": "abcd1234efgh5678",
            "identifier": f"{ix:>16}",
            "action": f"action_{ix}",
            "status": state,
            "created_at": "2025-12-05T19:07:40Z",
            "updated_at": "2025-12-05T19:08:40Z",
            "started_at": None if state == "pending" else "2025-12-05T19:09:40Z",
            "completed_at": None
            if state in ["pending", "running"]
            else "2025-12-05T19:10:40Z",
        }
        for ix, state in enumerate(states)
    ]
