from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from gateway.login_tokens import (
    BadLoginToken,
    ExpiredLoginToken,
    InvalidTokenUser,
    generate_login_token,
    human_memorable_token,
    strip_token,
    validate_login_token,
    validate_token_login_allowed,
)


def test_human_memorable_token_uses_three_words():
    token = human_memorable_token()

    assert len(token.split()) == 3


def test_generate_login_token_stores_hash_and_expiry(user):
    token = generate_login_token(user=user)

    user.refresh_from_db()

    assert token
    assert len(token.split()) == 3
    assert user.login_token != token
    assert check_password(strip_token(token), user.login_token)
    assert user.login_token_expires_at is not None


def test_validate_login_token_accepts_username_and_consumes_token(user):
    token = generate_login_token(user=user)

    validated_user = validate_login_token(user.username, token)

    assert validated_user == user

    user.refresh_from_db()
    assert user.login_token == ""
    assert user.login_token_expires_at is None


def test_validate_login_token_rejects_expired_token(user):
    token = generate_login_token(user=user)
    user.login_token_expires_at = timezone.now() - timedelta(minutes=1)
    user.save(update_fields=["login_token_expires_at"])

    with pytest.raises(ExpiredLoginToken):
        validate_login_token(user.username, token)


def test_validate_login_token_rejects_invalid_token(user):
    generate_login_token(user=user)

    with pytest.raises(BadLoginToken):
        validate_login_token(user.username, "wrong token")


def test_validate_login_token_rejects_reused_token(user):
    token = generate_login_token(user=user)

    validate_login_token(user.username, token)

    with pytest.raises(BadLoginToken):
        validate_login_token(user.username, token)


def test_validate_token_login_allowed_rejects_non_github_user():
    User = get_user_model()
    user = User.objects.create_user(username="plain-user")

    with pytest.raises(InvalidTokenUser):
        validate_token_login_allowed(user)


def test_validate_token_login_allowed_rejects_inactive_user(user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    with pytest.raises(InvalidTokenUser):
        validate_token_login_allowed(user)
