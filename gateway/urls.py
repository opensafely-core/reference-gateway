from django.urls import path

from . import views


urlpatterns = [
    path("", views.index),
    path("auth/login/", views.login, name="login"),
    path("auth/login/callback/", views.login_callback, name="login-callback"),
    path("auth/logout/", views.logout, name="logout"),
]
