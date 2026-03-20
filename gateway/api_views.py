import json

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Project


def _parse_json_body(request):
    """Returns (data, error_response). On failure, data is None."""
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)


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
    """Validate user by username or email; accept any token."""
    data, err = _parse_json_body(request)
    if err:
        return err
    user_field = data.get("user")
    if not user_field or "token" not in data:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    try:
        user = User.objects.get(username=user_field)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=user_field)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)
    return JsonResponse(_build_level4_user(user))


@csrf_exempt
@require_POST
def authorise(request):
    """Validate user by username only; skip Level 4 access checks."""
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
