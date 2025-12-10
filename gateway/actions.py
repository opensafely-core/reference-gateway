import base64
import secrets

from django.conf import settings

from . import github, rap_api
from .models import Job, Run


def start_run(*, project, user):
    """
    Start a run for the given project.
    """
    rap_id = _generate_rap_id()
    commit = github.get_latest_commit(settings.GITHUB_ORG, project.slug)
    rap_api.create(
        rap_id=rap_id, project=project, commit=commit, username=user.profile.username
    )
    return _create_run(rap_id=rap_id, project=project, user=user)


def update_run(*, run):
    """
    Update a run with data from the RAP Controller.
    """
    data = rap_api.status(rap_ids=[run.id])
    _create_or_update_jobs(run=run, jobs_data=data["jobs"])


def cancel_run(*, run):
    """
    Cancel a run.
    """
    rap_api.cancel(rap_id=run.id, actions=run.actions)
    _mark_run_cancelled(run=run)


def _create_run(*, rap_id, project, user):
    return Run.objects.create(id=rap_id, project=project, user=user)


def _create_or_update_jobs(*, run, jobs_data):
    for job_datum in jobs_data:
        job, _ = run.jobs.get_or_create(
            id=job_datum["identifier"],
            defaults={"action": job_datum["action"], "state": Job.State.PENDING},
        )
        job.state = Job.State(job_datum["status"])
        job.created_at = job_datum["created_at"]
        job.updated_at = job_datum["updated_at"]
        job.started_at = job_datum["started_at"]
        job.completed_at = job_datum["completed_at"]
        job.save()


def _mark_run_cancelled(*, run):
    run.cancelled = True
    run.save()


def _generate_rap_id():
    """
    Generate a random 16 character identifier to identify a run.
    """
    return base64.b32encode(secrets.token_bytes(10)).decode("ascii").lower()
