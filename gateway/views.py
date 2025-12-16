import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import github
from .actions import cancel_run, start_run, update_run
from .models import GitHubProfile, Project, Run


def projects(request):
    projects = Project.objects.order_by("name")

    return render(
        request,
        "projects.html",
        {"projects": projects},
    )


def project(request, name):
    project = get_object_or_404(Project, name=name)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        assert not project.has_in_progress_run()
        run = start_run(project=project, user=request.user)
        return redirect("run", run_id=run.id)

    runs = (
        project.runs_ordered_by_most_recent_start()
        .select_related("user")
        .prefetch_related("jobs")
    )

    return render(
        request,
        "project.html",
        {
            "project": project,
            "runs": runs,
            "can_start_run": request.user.is_authenticated
            and not project.has_in_progress_run(),
        },
    )


def run(request, run_id):
    run = get_object_or_404(Run, pk=run_id)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        assert run.in_progress
        cancel_run(run=run)
        return redirect("run", run_id=run.id)

    if run.in_progress:
        update_run(run=run)

    jobs = run.jobs_ordered_by_earliest_start()

    return render(
        request,
        "run.html",
        {
            "run": run,
            "jobs": jobs,
            "can_cancel": request.user.is_authenticated and run.in_progress,
        },
    )


def login(request):
    state = secrets.token_urlsafe(16)
    request.session["github_oauth_state"] = state
    redirect_uri = request.build_absolute_uri(reverse("login-callback"))
    params = {
        "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
        "allow_signup": "false",
        "scope": "read:user",
        "state": state,
        "redirect_uri": redirect_uri,
    }
    return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}")


def login_callback(request):
    expected_state = request.session.pop("github_oauth_state", None)
    state = request.GET.get("state")
    code = request.GET.get("code")
    if not state or state != expected_state or not code:
        return HttpResponseBadRequest("Invalid login attempt.")

    token = github.exchange_code_for_token(code)
    user_data = github.get_user_for_token(token)

    try:
        profile = GitHubProfile.objects.get(github_id=user_data["id"])
    except GitHubProfile.DoesNotExist:
        return HttpResponseForbidden("Access denied.")

    if not profile.user.is_active:
        return HttpResponseForbidden("Access denied.")

    auth.login(request, profile.user)
    return redirect("/")


@require_POST
def logout(request):
    auth.logout(request)
    return redirect("/")
