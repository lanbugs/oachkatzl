"""Test configuration — mongomock + Celery always-eager."""
from __future__ import annotations

import os

import mongomock
import mongoengine
import pytest

# Must be set before any app import
os.environ.setdefault("OACHKATZL_MONGO_URI", "mongodb://localhost:27017/testdb")
os.environ.setdefault("OACHKATZL_REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("OACHKATZL_JWT_SECRET", "test-secret-key")
os.environ.setdefault("OACHKATZL_ENCRYPTION_KEY", "bWF4b3JjaC1kZXYta2V5LWRvLW5vdC11c2UtMDAwMDA=")


@pytest.fixture(scope="session")
def app():
    mongoengine.disconnect_all()
    # Use mongomock as the MongoClient — mongoengine picks it up via mongo_client_class
    mongoengine.connect(
        "testdb",
        host="localhost",
        port=27017,
        mongo_client_class=mongomock.MongoClient,
    )

    from app import create_app
    from app.celery_app import celery

    celery.conf.update(task_always_eager=True, task_eager_propagates=False)

    application = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})
    yield application

    mongoengine.disconnect_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db():
    """Drop all collections before each test."""
    yield
    from app.models import (
        User, ApiToken, Project, ProjectMember, AccessKey, Repository,
        Inventory, Environment, View, Template, Schedule, Task, TaskLog,
        Integration, Runner, NotificationSetting, Event, Option, CustomApp,
    )
    for cls in (
        User, ApiToken, Project, ProjectMember, AccessKey, Repository,
        Inventory, Environment, View, Template, Schedule, Task, TaskLog,
        Integration, Runner, NotificationSetting, Event, Option, CustomApp,
    ):
        cls.drop_collection()


@pytest.fixture
def admin_user():
    from app.models.user import User
    from app.services.auth_service import hash_password
    return User(
        username="admin", email="admin@test.com", name="Admin",
        password_hash=hash_password("adminpass"), is_admin=True, active=True,
    ).save()


@pytest.fixture
def regular_user():
    from app.models.user import User
    from app.services.auth_service import hash_password
    return User(
        username="alice", email="alice@test.com", name="Alice",
        password_hash=hash_password("alicepass"), is_admin=False, active=True,
    ).save()


@pytest.fixture
def admin_token(client, admin_user):
    rv = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
    return rv.get_json()["token"]


@pytest.fixture
def user_token(client, regular_user):
    rv = client.post("/api/auth/login", json={"username": "alice", "password": "alicepass"})
    return rv.get_json()["token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def project(admin_user):
    from app.models.project import Project, ProjectMember
    p = Project(name="Test Project").save()
    ProjectMember(project=p, user=admin_user, role="owner").save()
    return p
