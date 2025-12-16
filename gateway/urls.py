from django.urls import path

from . import views


urlpatterns = [
    path("", views.projects, name="projects"),
    path("projects/<slug:name>/", views.project, name="project"),
    path("runs/<str:run_id>/", views.run, name="run"),
    path("auth/login/", views.login, name="login"),
    path("auth/login/callback/", views.login_callback, name="login-callback"),
    path("auth/logout/", views.logout, name="logout"),
]
