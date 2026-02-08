"""
Fixtures de test pour l'API ansibase
Utilise la base PostgreSQL réelle (les migrations doivent être appliquées)
"""

import secrets

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.user import ApiKey, User
from app.services.crypto import encrypt_api_key


# engine et session pour les tests (meme base, avec rollback par test)
_engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture()
def db() -> Session:
    """Session DB avec rollback automatique après chaque test"""
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    """Client HTTP de test avec override de la session DB"""

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db: Session) -> User:
    """Utilisateur admin existant en base (cree par la migration)"""
    user = db.execute(
        text("SELECT * FROM ansibase_users WHERE username = :u"),
        {"u": "admin"},
    ).fetchone()
    if user:
        return db.get(User, user.id)

    # fallback : creer si absent (avec sa cle API par defaut)
    raw_key = secrets.token_urlsafe(48)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username="admin",
        password_hash=bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8"),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.flush()

    # on cree la cle API par defaut pour que le login fonctionne
    default_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_value_encrypted=encrypt_api_key(db, raw_key),
        key_prefix=raw_key[:12],
        name="default",
    )
    db.add(default_key)
    db.flush()
    return user


@pytest.fixture()
def admin_api_key(db: Session, admin_user: User) -> tuple[ApiKey, str]:
    """API Key active pour l'admin. Retourne (ApiKey, cle en clair)."""
    raw_key = secrets.token_urlsafe(48)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    api_key = ApiKey(
        user_id=admin_user.id,
        key_hash=key_hash,
        key_value_encrypted=encrypt_api_key(db, raw_key),
        key_prefix=raw_key[:12],
        name="test-key",
    )
    db.add(api_key)
    db.flush()
    return api_key, raw_key


@pytest.fixture()
def auth_headers(admin_api_key: tuple[ApiKey, str]) -> dict[str, str]:
    """Headers d'authentification prets a l'emploi"""
    _, raw_key = admin_api_key
    return {"Authorization": f"Bearer {raw_key}"}


@pytest.fixture()
def regular_user(db: Session) -> User:
    """Utilisateur non-superuser"""
    user = User(
        username="regular_user",
        password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8"),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def regular_api_key(db: Session, regular_user: User) -> tuple[ApiKey, str]:
    """API Key pour l'utilisateur non-superuser"""
    raw_key = secrets.token_urlsafe(48)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    api_key = ApiKey(
        user_id=regular_user.id,
        key_hash=key_hash,
        key_value_encrypted=encrypt_api_key(db, raw_key),
        key_prefix=raw_key[:12],
        name="regular-test-key",
    )
    db.add(api_key)
    db.flush()
    return api_key, raw_key


@pytest.fixture()
def regular_auth_headers(regular_api_key: tuple[ApiKey, str]) -> dict[str, str]:
    """Headers d'authentification pour utilisateur non-superuser"""
    _, raw_key = regular_api_key
    return {"Authorization": f"Bearer {raw_key}"}
