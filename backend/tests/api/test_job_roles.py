from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.v1.candidate.interview_router import get_job_role_repository
from app.core.exceptions import AuthenticationError
from app.main import create_app


def _candidate() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada Lovelace",
        email="ada@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )


class _FakeJobRoleRepository:
    async def list_active(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                name="AI Engineer",
                description="Build and deploy production AI systems.",
                requirements=["Python", "Model deployment"],
                skills=["Python", "MLOps"],
                experience_min=Decimal("2.00"),
                experience_max=Decimal("6.00"),
                is_active=True,
            )
        ]


class _MalformedJobRoleRepository:
    async def list_active(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                name="Malformed Role",
                description=None,
                requirements={"not": "an array"},
                skills=["Python", 42, "", "x" * 200],
                experience_min=None,
                experience_max=None,
                is_active=True,
            )
        ]


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_active_role_catalog_requires_authentication(client: TestClient) -> None:
    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Authentication is required.")

    client.app.dependency_overrides[get_current_user] = _raise

    response = client.get("/api/v1/candidate/interviews/job-roles")

    assert response.status_code == 401


def test_active_role_catalog_returns_structured_database_roles(
    client: TestClient,
) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    client.app.dependency_overrides[get_job_role_repository] = (
        _FakeJobRoleRepository
    )

    response = client.get("/api/v1/candidate/interviews/job-roles")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "name": "AI Engineer",
            "description": "Build and deploy production AI systems.",
            "requirements": ["Python", "Model deployment"],
            "skills": ["Python", "MLOps"],
            "experience_min": 2.0,
            "experience_max": 6.0,
        }
    ]
    assert all(role["name"] != "Other" for role in response.json())


def test_active_role_catalog_normalizes_malformed_json_without_500(
    client: TestClient,
) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    client.app.dependency_overrides[get_job_role_repository] = (
        _MalformedJobRoleRepository
    )

    response = client.get("/api/v1/candidate/interviews/job-roles")

    assert response.status_code == 200, response.text
    assert response.json()[0]["requirements"] == []
    assert response.json()[0]["skills"] == ["Python"]
