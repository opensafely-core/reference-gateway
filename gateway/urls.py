from django.urls import path

from . import api_views, views


urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("", views.projects, name="projects"),
    path("projects/<slug:name>/", views.project, name="project"),
    path("runs/<str:run_id>/", views.run, name="run"),
    path("auth/airlock-token/", views.airlock_token, name="airlock-token"),
    path("auth/login/", views.login, name="login"),
    path("auth/login/callback/", views.login_callback, name="login-callback"),
    path("auth/logout/", views.logout, name="logout"),
    path(
        "api/v2/releases/authenticate", api_views.authenticate, name="api-authenticate"
    ),
    path("api/v2/releases/authorise", api_views.authorise, name="api-authorise"),
]
