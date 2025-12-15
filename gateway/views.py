import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import github
from .models import GitHubProfile


def index(request):
    return render(request, "index.html")


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
