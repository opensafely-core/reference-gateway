from datetime import timedelta

from django.utils import timezone

from gateway.actions import _create_or_update_jobs, _create_run, _mark_run_cancelled
from gateway.models import Job, Run


def test_user_display_name_uses_full_name(user):
    user.full_name = "Alice Example"

    assert user.display_name == "Alice Example"


def test_user_display_name_falls_back_to_username(user):
    assert user.display_name == "alice"


def test_project_has_in_progress_run(project, user):
    assert not project.has_in_progress_run()
    _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    assert project.has_in_progress_run()


def test_project_runs_ordered_by_most_recent_start(project, user):
    now = timezone.now()

    run1 = Run.objects.create(id="0000000000000001", project=project, user=user)
    run2 = Run.objects.create(id="0000000000000002", project=project, user=user)
    run3 = Run.objects.create(id="0000000000000003", project=project, user=user)

    run1.jobs.create(
        id="aaa",
        action="action",
        state=Job.State.SUCCEEDED,
        started_at=now - timedelta(hours=2),
    )
    run2.jobs.create(
        id="bbb",
        action="action",
        state=Job.State.RUNNING,
        started_at=now - timedelta(hours=1),
    )

    runs = list(project.runs_ordered_by_most_recent_start())
    assert runs == [run3, run2, run1]


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


def test_run_jobs_ordered_by_earliest_start(project, user):
    run = _create_run(rap_id="abcd1234efgh5678", project=project, user=user)
    now = timezone.now()

    job1 = run.jobs.create(
        id="aaa",
        action="action-1",
        state=Job.State.RUNNING,
        created_at=now,
        started_at=now - timedelta(minutes=2),
    )
    job2 = run.jobs.create(
        id="bbb",
        action="action-2",
        state=Job.State.RUNNING,
        created_at=now,
        started_at=now - timedelta(minutes=1),
    )
    job3 = run.jobs.create(
        id="ccc",
        action="action-3",
        state=Job.State.PENDING,
        created_at=now,
        started_at=None,
    )

    jobs = list(run.jobs_ordered_by_earliest_start())
    assert jobs == [job1, job2, job3]


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
