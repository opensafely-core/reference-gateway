import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Project, User


class BackendAuthenticationError(Exception):
    pass


def _parse_json_body(request):
    """Returns (data, error_response). On failure, data is None."""
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


def _authenticate_backend(request):
    token = request.headers.get("Authorization")
    if token is None:
        raise BackendAuthenticationError("Authorization header is missing")
    if token == "":
        raise BackendAuthenticationError("Authorization header is empty")
    if token != settings.AIRLOCK_TOKEN:
        raise BackendAuthenticationError("Invalid token")


def _build_level4_user(user):
    workspaces = {}
    for project in Project.objects.order_by("name"):
        workspaces[project.name] = {
            "project_details": {
                "name": project.name,
                "ongoing": True,
                "orgs": [],
            },
            "archived": False,
        }
    return {
        "username": user.username,
        "fullname": user.get_full_name() or user.username,
        "workspaces": workspaces,
        "copiloted_workspaces": {},
        "output_checker": False,
    }


@csrf_exempt
@require_POST
def authenticate(request):
    """Validate user by username only; accept any token."""
    try:
        _authenticate_backend(request)
    except BackendAuthenticationError as exc:
        return JsonResponse({"detail": str(exc)}, status=401)
    data, err = _parse_json_body(request)
    if err:
        return err
    user_field = data.get("user")
    if not user_field or "token" not in data:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    try:
        user = User.objects.get(username=user_field)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    return JsonResponse(_build_level4_user(user))


@csrf_exempt
@require_POST
def authorise(request):
    """Validate user by username only; skip Level 4 access checks."""
    try:
        _authenticate_backend(request)
    except BackendAuthenticationError as exc:
        return JsonResponse({"detail": str(exc)}, status=401)
    data, err = _parse_json_body(request)
    if err:
        return err
    user_field = data.get("user")
    if not user_field:
        return JsonResponse({"error": "Missing required field: user"}, status=400)
    try:
        user = User.objects.get(username=user_field)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    return JsonResponse(_build_level4_user(user))
