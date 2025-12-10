import pytest
from django.contrib.auth.models import User

from gateway.models import GitHubProfile, Project


@pytest.fixture(autouse=True)
def enable_db_for_all_tests(db):
    yield


@pytest.fixture
def project():
    return Project.objects.create(slug="example", description="Example project")


@pytest.fixture
def user():
    user = User.objects.create_user(username="alice", email="alice@example.com")
    GitHubProfile.objects.create(id=123, username="alice-gh", user=user)
    return user
