import os
from collections.abc import AsyncIterator

import pytest
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Must be set before app imports: Settings() is constructed at import time
# and raises ValidationError if SECRET_KEY is missing.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")

from uuid_utils import uuid7

from app.core.config import settings
from app.core.security import hash_password
from app.db.redis import get_redis_client
from app.db.session import get_session
from app.main import app  # noqa: E402
from app.models.platform_template import PlatformTemplate
from app.models.user import User


def create_db_engine() -> AsyncEngine:
    """Create test engine using the same Neon database but with isolated test data."""
    db_url = str(settings.DATABASE_URL)

    test_engine = create_async_engine(
        db_url,
        poolclass=NullPool,
    )
    return test_engine


@pytest.fixture(scope="session")
async def setup_db() -> AsyncIterator[None]:
    # Create all tables in the test database
    test_engine = create_db_engine()

    # Don't drop/create tables - use existing database
    # Just ensure the engine is available for tests
    yield

    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_db: None) -> AsyncIterator[AsyncSession]:
    test_engine = create_db_engine()

    TestingSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with TestingSessionLocal() as session:
        yield session

    # Don't clean up tables - just dispose the engine
    await test_engine.dispose()


@pytest.fixture
def fake_redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def reset_limiter() -> None:
    from app.core.rate_limit import limiter

    limiter.reset()


@pytest.fixture
async def client(
    db_session: AsyncSession, fake_redis: FakeAsyncRedis
) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_get_redis() -> AsyncIterator[FakeAsyncRedis]:
        yield fake_redis

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_redis_client] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for authentication tests."""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
async def seed_platform_templates(db_session: AsyncSession) -> None:
    """Seed platform templates for all tests."""
    templates = [
        PlatformTemplate(
            id=str(uuid7()),
            title="Classic",
            description="Balanced text-and-logo layout for most organisers.",
            thumbnail_url="https://res.cloudinary.com/social-badge/image/upload/v1/platform-thumbnails/classic.png",
            preview_image_url="https://res.cloudinary.com/social-badge/image/upload/v1/platform-previews/classic.png",
            is_active=True,
        ),
        PlatformTemplate(
            id=str(uuid7()),
            title="Minimal",
            description="Simple layout with extra whitespace for clean branding.",
            thumbnail_url="https://res.cloudinary.com/social-badge/image/upload/v1/platform-thumbnails/minimal.png",
            preview_image_url="https://res.cloudinary.com/social-badge/image/upload/v1/platform-previews/minimal.png",
            is_active=True,
        ),
    ]

    for template in templates:
        db_session.add(template)
    await db_session.commit()


@pytest.fixture
def valid_signup_payload() -> dict[str, str]:
    return {
        "name": "API Test User",
        "email": "apitest@example.com",
        "password": "StrongPassword1!",  # noqa: S106
    }
