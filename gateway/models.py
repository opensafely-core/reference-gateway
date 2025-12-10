import enum

from django.conf import settings
from django.db import models
from django_enum import EnumField


class GitHubProfile(models.Model):
    id = models.IntegerField(primary_key=True)
    # 39 is the maximum length of a GitHub username
    username = models.CharField(max_length=39)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )


class Project(models.Model):
    slug = models.SlugField(unique=True)
    # 350 is the maximum length of a description in the GitHub web UI
    description = models.CharField(max_length=350, blank=True)


class Run(models.Model):
    class State(enum.Enum):
        PENDING = "pending"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        CANCELLED = "cancelled"

    id = models.CharField(primary_key=True, max_length=16)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    cancelled = models.BooleanField(default=False)

    @property
    def actions(self):
        return {job.action for job in self.jobs.all()}

    @property
    def state(self):
        if self.cancelled:
            return Run.State.CANCELLED

        job_states = [job.state for job in self.jobs.all()]
        if all(state == Job.State.PENDING for state in job_states):
            return Run.State.PENDING
        if all(state == Job.State.SUCCEEDED for state in job_states):
            return Run.State.SUCCEEDED
        if any(state == Job.State.FAILED for state in job_states):
            return Run.State.FAILED
        else:
            return Run.State.RUNNING


class Job(models.Model):
    class State(enum.Enum):
        # These match the values defined in job-runner's controller.models.State.
        PENDING = "pending"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"

    id = models.CharField(primary_key=True, max_length=16)
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    action = models.CharField(max_length=200)
    state = EnumField(State)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
