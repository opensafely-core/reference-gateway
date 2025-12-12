import pytest
from django.contrib.auth.models import User

from gateway.models import GitHubProfile, Project


@pytest.fixture(autouse=True)
def enable_db_for_all_tests(db):
    yield


@pytest.fixture
def project():
    return Project.objects.create(id=123, name="example", description="Example project")


@pytest.fixture
def user():
    return User.objects.create_user(
        username="alice", profile=GitHubProfile(github_id=123)
    )
