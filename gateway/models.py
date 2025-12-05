from django.conf import settings
from django.db import models


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


class Job(models.Model):
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    action = models.CharField(max_length=200)
    status_code = models.CharField(max_length=100)
    status_message = models.CharField(max_length=100)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
