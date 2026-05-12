import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.token import create_access_token
from app.models import OrganiserTemplate, PlatformTemplate, User


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a verified user for authenticated requests."""
    user = User(
        first_name="Test",
        last_name="Organiser",
        email="organiser@example.com",
        password_hash=hash_password("StrongPassword1!"),
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Return a Bearer token header for the test user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def platform_template(db_session: AsyncSession) -> PlatformTemplate:
    """Seed a single platform template for tests."""
    template = PlatformTemplate(
        title="Test Layout",
        canvas_data={"layout": "test-v1"},
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


async def test_create_instance_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    platform_template: PlatformTemplate,
    test_user: User,
) -> None:
    response = await client.post(
        "/api/v1/templates/instances",
        headers=auth_headers,
        json={"platform_template_id": str(platform_template.id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Template instance created successfully."
    assert data["data"]["platform_template_id"] == str(platform_template.id)
    assert data["data"]["organizer_id"] == str(test_user.id)
    assert "instance_id" in data["data"]
    assert "created_at" in data["data"]


async def test_create_instance_unauthenticated(
    client: AsyncClient, platform_template: PlatformTemplate
) -> None:
    response = await client.post(
        "/api/v1/templates/instances",
        json={"platform_template_id": str(platform_template.id)},
    )
    assert response.status_code in (401, 403)


async def test_create_instance_platform_template_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    fake_id = uuid.uuid4()
    response = await client.post(
        "/api/v1/templates/instances",
        headers=auth_headers,
        json={"platform_template_id": str(fake_id)},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Platform template not found."


async def test_create_instance_missing_field(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/templates/instances",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 422


# ── logo upload ────────────────────────────────────────────────────────────────

_FAKE_PNG = b"fake-png-bytes"
_FAKE_URL = "https://res.cloudinary.com/demo/image/upload/template-logos/abc.png"
_FAKE_PUBLIC_ID = "template-logos/abc"


@pytest.fixture
async def template_instance(
    db_session: AsyncSession,
    test_user: User,
    platform_template: PlatformTemplate,
) -> OrganiserTemplate:
    """Organiser template instance owned by test_user, no logo yet."""
    instance = OrganiserTemplate(
        organizer_id=test_user.id,
        platform_template_id=platform_template.id,
        title="My Template",
        canvas_data={},
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)
    return instance


@pytest.fixture
async def template_instance_with_logo(
    db_session: AsyncSession,
    test_user: User,
    platform_template: PlatformTemplate,
) -> OrganiserTemplate:
    """Organiser template instance that already has an uploaded logo."""
    instance = OrganiserTemplate(
        organizer_id=test_user.id,
        platform_template_id=platform_template.id,
        title="My Template With Logo",
        canvas_data={},
        logo_url="https://old-logo.example.com/logo.png",
        logo_public_id="template-logos/old-logo-id",
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)
    return instance


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """A second user who does NOT own the template_instance fixture."""
    user = User(
        first_name="Other",
        last_name="User",
        email="other-organiser@example.com",
        password_hash=hash_password("StrongPassword1!"),
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def other_auth_headers(other_user: User) -> dict[str, str]:
    token = create_access_token(other_user.id)
    return {"Authorization": f"Bearer {token}"}


@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_success(
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
    template_instance: OrganiserTemplate,
) -> None:
    mock_upload.return_value = (_FAKE_URL, _FAKE_PUBLIC_ID)

    response = await client.put(
        f"/api/v1/templates/instances/{template_instance.id}/logo",
        headers=auth_headers,
        files={"file": ("logo.png", _FAKE_PNG, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Logo uploaded successfully."
    assert data["data"]["logo_url"] == _FAKE_URL
    mock_upload.assert_called_once_with(_FAKE_PNG)


@patch("app.services.template_service.delete_logo", new_callable=AsyncMock)
@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_replaces_existing(
    mock_upload: AsyncMock,
    mock_delete: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
    template_instance_with_logo: OrganiserTemplate,
) -> None:
    """Uploading a new logo should delete the old Cloudinary asset first."""
    mock_upload.return_value = (_FAKE_URL, _FAKE_PUBLIC_ID)

    response = await client.put(
        f"/api/v1/templates/instances/{template_instance_with_logo.id}/logo",
        headers=auth_headers,
        files={"file": ("logo.jpg", _FAKE_PNG, "image/jpeg")},
    )

    assert response.status_code == 200
    mock_delete.assert_called_once_with("template-logos/old-logo-id")
    mock_upload.assert_called_once()


@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_unsupported_type(
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
    template_instance: OrganiserTemplate,
) -> None:
    response = await client.put(
        f"/api/v1/templates/instances/{template_instance.id}/logo",
        headers=auth_headers,
        files={"file": ("logo.gif", b"fake-gif-bytes", "image/gif")},
    )

    assert response.status_code == 415
    data = response.json()
    assert data["status"] == "error"
    mock_upload.assert_not_called()


@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_too_large(
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
    template_instance: OrganiserTemplate,
) -> None:
    oversized = b"x" * (2 * 1024 * 1024 + 1)

    response = await client.put(
        f"/api/v1/templates/instances/{template_instance.id}/logo",
        headers=auth_headers,
        files={"file": ("logo.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    data = response.json()
    assert data["status"] == "error"
    mock_upload.assert_not_called()


async def test_upload_logo_unauthenticated(
    client: AsyncClient,
    template_instance: OrganiserTemplate,
) -> None:
    response = await client.put(
        f"/api/v1/templates/instances/{template_instance.id}/logo",
        files={"file": ("logo.png", _FAKE_PNG, "image/png")},
    )

    assert response.status_code in (401, 403)


@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_instance_not_found(
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.put(
        f"/api/v1/templates/instances/{uuid.uuid4()}/logo",
        headers=auth_headers,
        files={"file": ("logo.png", _FAKE_PNG, "image/png")},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "Template instance not found."
    mock_upload.assert_not_called()


async def test_upload_logo_forbidden(
    client: AsyncClient,
    other_auth_headers: dict[str, str],
    template_instance: OrganiserTemplate,
) -> None:
    """A user who does not own the instance should get 403."""
    response = await client.put(
        f"/api/v1/templates/instances/{template_instance.id}/logo",
        headers=other_auth_headers,
        files={"file": ("logo.png", _FAKE_PNG, "image/png")},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["status"] == "error"


@patch("app.services.template_service.delete_logo", new_callable=AsyncMock)
@patch("app.services.template_service.upload_logo", new_callable=AsyncMock)
async def test_upload_logo_rate_limit(
    mock_upload: AsyncMock,
    mock_delete: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
    template_instance: OrganiserTemplate,
) -> None:
    mock_upload.return_value = (_FAKE_URL, _FAKE_PUBLIC_ID)

    url = f"/api/v1/templates/instances/{template_instance.id}/logo"
    for _ in range(10):
        await client.put(
            url,
            headers=auth_headers,
            files={"file": ("logo.png", _FAKE_PNG, "image/png")},
        )

    response = await client.put(
        url,
        headers=auth_headers,
        files={"file": ("logo.png", _FAKE_PNG, "image/png")},
    )
    assert response.status_code == 429
    data = response.json()
    assert data["status"] == "error"
