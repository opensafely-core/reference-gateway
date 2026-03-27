import base64
import logging
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug

from . import github, rap_api
from .models import Job, Project, Run, User


logger = logging.getLogger(__name__)


def create_or_update_projects():
    for record in github.get_repo_metadata(settings.GITHUB_ORG):
        try:
            validate_slug(record["name"])
        except ValidationError:
            logger.warning(
                "Ignoring GitHub repo with invalid slug name: %s", record["name"]
            )
            continue
        Project.objects.update_or_create(
            id=record["id"],
            defaults={
                "name": record["name"],
                "description": record["description"] or "",
            },
        )


def create_or_update_users():
    User.objects.update(is_active=False)
    # The scheduled org sync currently only refreshes GitHub id and username.
    # Richer profile metadata such as full_name is updated on interactive login.
    for record in github.get_user_metadata(settings.GITHUB_ORG):
        github_id = record["id"]
        if User.objects.filter(github_id=github_id).exists():
            user = User.objects.get(github_id=github_id)
            user.is_active = True
            user.username = record["login"]
            user.save()
        else:
            User.objects.create_user(
                username=record["login"], github_id=github_id, is_active=True
            )


def start_run(*, project, user):
    """
    Start a run for the given project.
    """
    rap_id = _generate_rap_id()
    commit = github.get_latest_commit(settings.GITHUB_ORG, project.name)
    rap_api.create(
        rap_id=rap_id, project_name=project.name, commit=commit, username=user.username
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
    rap_api.cancel(rap_id=run.id, actions=list(run.actions))
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
