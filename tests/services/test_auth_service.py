from unittest.mock import AsyncMock, patch

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailConflictError, GoogleOAuthError
from app.core.security import verify_password
from app.core.token import store_google_oauth_state
from app.models.auth_provider import AuthProvider
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.services.auth_service import (
    authenticate_with_google,
    build_google_auth_url,
    signup,
)


def _make_payload(email: str = "jane@example.com") -> SignupRequest:
    return SignupRequest(
        name="Jane Doe",
        email=email,
        password="StrongPassword1!",  # noqa: S106
    )


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_creates_user(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("create@example.com")
    await signup(db_session, fake_redis, payload)

    result = await db_session.execute(
        select(User).where(User.email == "create@example.com")
    )
    user = result.scalars().first()
    assert user is not None
    assert user.name == "Jane Doe"


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_hashes_password(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("hash@example.com")
    await signup(db_session, fake_redis, payload)

    result = await db_session.execute(
        select(User).where(User.email == "hash@example.com")
    )
    user = result.scalars().first()
    assert user is not None
    assert user.password_hash is not None
    assert verify_password(payload.password, user.password_hash) is True


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_creates_email_auth_provider(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("provider@example.com")
    await signup(db_session, fake_redis, payload)

    result = await db_session.execute(
        select(User).where(User.email == "provider@example.com")
    )
    user = result.scalars().first()
    assert user is not None

    provider_result = await db_session.execute(
        select(AuthProvider).where(AuthProvider.user_id == user.id)
    )
    provider = provider_result.scalars().first()
    assert provider is not None
    assert provider.provider == "email"


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_stores_verification_token(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("token@example.com")
    await signup(db_session, fake_redis, payload)

    keys = await fake_redis.keys("verify:*")
    assert len(keys) == 1


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_sends_verification_email(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("email@example.com")
    await signup(db_session, fake_redis, payload)

    mock_email.assert_called_once()
    assert mock_email.call_args[0][0] == "email@example.com"


@patch("app.services.auth_service.send_verification_email", new_callable=AsyncMock)
async def test_signup_rejects_duplicate_email(
    mock_email: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    payload = _make_payload("duplicate@example.com")
    await signup(db_session, fake_redis, payload)

    duplicate = _make_payload("duplicate@example.com")
    with pytest.raises(EmailConflictError):
        await signup(db_session, fake_redis, duplicate)


async def test_build_google_auth_url_stores_state(fake_redis: FakeAsyncRedis) -> None:
    auth_url = await build_google_auth_url(fake_redis)

    assert "accounts.google.com" in auth_url
    state = auth_url.split("state=")[1].split("&")[0]
    stored_state = await fake_redis.get(f"oauth:google:state:{state}")
    assert stored_state == "1"


@patch("app.services.auth_service._fetch_google_userinfo", new_callable=AsyncMock)
@patch("app.services.auth_service._exchange_google_code", new_callable=AsyncMock)
async def test_authenticate_with_google_creates_new_user(
    mock_exchange: AsyncMock,
    mock_userinfo: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    await store_google_oauth_state(fake_redis, "valid-state")
    mock_exchange.return_value = {"access_token": "token"}
    mock_userinfo.return_value = {
        "email": "google@example.com",
        "name": "Google User",
        "picture": "https://example.com/photo.jpg",
    }

    user, is_new_user = await authenticate_with_google(
        db_session, fake_redis, "auth-code", "valid-state"
    )

    assert is_new_user is True
    assert user.email == "google@example.com"
    assert user.is_email_verified is True
    assert user.profile_photo_url == "https://example.com/photo.jpg"

    provider_result = await db_session.execute(
        select(AuthProvider).where(AuthProvider.user_id == user.id)
    )
    provider = provider_result.scalars().first()
    assert provider is not None
    assert provider.provider == "google"


@patch("app.services.auth_service._fetch_google_userinfo", new_callable=AsyncMock)
@patch("app.services.auth_service._exchange_google_code", new_callable=AsyncMock)
async def test_authenticate_with_google_links_existing_user(
    mock_exchange: AsyncMock,
    mock_userinfo: AsyncMock,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    existing_user = User(
        name="Existing User",
        email="existing@example.com",
        is_email_verified=False,
    )
    db_session.add(existing_user)
    await db_session.commit()
    await db_session.refresh(existing_user)

    await store_google_oauth_state(fake_redis, "valid-state")
    mock_exchange.return_value = {"access_token": "token"}
    mock_userinfo.return_value = {
        "email": "existing@example.com",
        "name": "Existing User",
        "picture": "https://example.com/google-photo.jpg",
    }

    user, is_new_user = await authenticate_with_google(
        db_session, fake_redis, "auth-code", "valid-state"
    )

    assert is_new_user is False
    assert user.id == existing_user.id
    assert user.is_email_verified is True
    assert user.profile_photo_url == "https://example.com/google-photo.jpg"

    provider_result = await db_session.execute(
        select(AuthProvider).where(
            AuthProvider.user_id == existing_user.id,
            AuthProvider.provider == "google",
        )
    )
    provider = provider_result.scalars().first()
    assert provider is not None


async def test_authenticate_with_google_rejects_invalid_state(
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> None:
    with pytest.raises(GoogleOAuthError, match="Invalid or expired Google OAuth state"):
        await authenticate_with_google(db_session, fake_redis, "auth-code", "missing")
