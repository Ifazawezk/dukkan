import os

# Configure the app for tests before anything imports it.
os.environ["DUKKAN_DATABASE_URL"] = "sqlite://"
os.environ["DUKKAN_BCRYPT_ROUNDS"] = "4"
os.environ["DUKKAN_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db, make_engine
from app.main import create_app
from app.models import Branch, Role, User
from app.security import create_access_token, hash_password

PASSWORD = "password123"


@pytest.fixture
def engine():
    # One shared in-memory database per test.
    engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory):
    app = create_app()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def branch(db):
    branch = Branch(code="DOH", name="Doha", name_ar="الدوحة")
    db.add(branch)
    db.commit()
    return branch


@pytest.fixture
def users(db, branch) -> dict[str, User]:
    """One active user per role, all in the test branch."""
    created = {}
    for role in Role:
        user = User(
            username=role.value,
            full_name=f"Test {role.value}",
            password_hash=hash_password(PASSWORD),
            role=role,
            branch_id=branch.id,
        )
        db.add(user)
        created[role.value] = user
    db.commit()
    return created


def bearer(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(users) -> dict[str, dict[str, str]]:
    """Authorization headers keyed by role name."""
    return {name: bearer(user) for name, user in users.items()}
