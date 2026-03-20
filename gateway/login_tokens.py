from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from xkcdpass import xkcd_password


WORDLIST = xkcd_password.generate_wordlist("eff-long")


class TokenLoginException(Exception):
    pass


class BadLoginToken(TokenLoginException):
    pass


class ExpiredLoginToken(TokenLoginException):
    pass


class InvalidTokenUser(TokenLoginException):
    pass


def strip_token(token):
    return token.strip().replace(" ", "")


def validate_token_login_allowed(user):
    if not user.github_id:
        raise InvalidTokenUser(f"User {user.username} is not a github user")

    if not user.is_active:
        raise InvalidTokenUser(f"User {user.username} is inactive")


def human_memorable_token():
    return xkcd_password.generate_xkcdpassword(WORDLIST, numwords=3)


def generate_login_token(*, user):
    validate_token_login_allowed(user)

    token = human_memorable_token()
    user.login_token = make_password(strip_token(token))
    user.login_token_expires_at = timezone.now() + timedelta(hours=1)
    user.save(update_fields=["login_token", "login_token_expires_at"])
    return token


def validate_login_token(username, token):
    User = get_user_model()

    user = User.objects.get(username=username)
    validate_token_login_allowed(user)

    if not (user.login_token and user.login_token_expires_at):
        raise BadLoginToken(f"No login token set for {user.username}")

    if timezone.now() > user.login_token_expires_at:
        raise ExpiredLoginToken(f"Token for {user.username} has expired")

    if not check_password(strip_token(token), user.login_token):
        raise BadLoginToken(f"Token for {user.username} was invalid")

    user.login_token = ""
    user.login_token_expires_at = None
    user.save(update_fields=["login_token", "login_token_expires_at"])
    return user
