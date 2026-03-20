import enum

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Case, IntegerField, Min, When
from django_enum import EnumField


class User(AbstractUser):
    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    full_name = models.TextField(blank=True)
    login_token = models.CharField(max_length=128, blank=True)
    login_token_expires_at = models.DateTimeField(null=True, blank=True)

    def get_full_name(self):
        return self.full_name or super().get_full_name()

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class Project(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.SlugField(unique=True)
    # 350 is the maximum length of a description in the GitHub web UI
    description = models.CharField(max_length=350, blank=True)

    def has_in_progress_run(self):
        return bool([r for r in self.runs.all() if r.in_progress])

    def runs_ordered_by_most_recent_start(self):
        return self.runs.annotate(run_started_at=Min("jobs__started_at")).order_by(
            Case(
                When(run_started_at__isnull=True, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            "-run_started_at",
        )


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

    @property
    def in_progress(self):
        return self.state in [Run.State.PENDING, Run.State.RUNNING]

    def jobs_ordered_by_earliest_start(self):
        return self.jobs.order_by(
            Case(
                When(started_at__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
            "started_at",
            "id",
        )


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
