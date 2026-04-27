from collections.abc import Generator
from contextlib import contextmanager
import inspect

import anyio
import anyio.to_thread
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_session
from app.main import app
from app.models.base import Base
from app.models.queue import QueueModel
from app.models.task import TaskModel
import app.services.tasks as task_service_module


class SameThreadPortal:
    def call(self, func, *args):  # type: ignore[no-untyped-def]
        result = func(*args)
        if inspect.isawaitable(result):
            return anyio.run(lambda: result)
        return result


class SameThreadTestClient(TestClient):
    @contextmanager
    def _portal_factory(self) -> Generator[SameThreadPortal, None, None]:
        yield SameThreadPortal()


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[int] = []
        self.revoked: list[str] = []
        self.enqueue_errors: list[Exception] = []

    def enqueue(self, task_id: int) -> str:
        self.enqueued.append(task_id)
        if self.enqueue_errors:
            raise self.enqueue_errors.pop(0)
        return f"celery-{task_id}-{len(self.enqueued)}"

    def revoke(self, celery_task_id: str) -> None:
        self.revoked.append(celery_task_id)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def dispatcher(monkeypatch: pytest.MonkeyPatch) -> FakeDispatcher:
    fake_dispatcher = FakeDispatcher()
    monkeypatch.setattr(task_service_module, "dispatcher", fake_dispatcher)
    return fake_dispatcher


@pytest.fixture()
def client(
    db_session: Session,
    dispatcher: FakeDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    async def run_sync_inline(func, *args, **kwargs):  # type: ignore[no-untyped-def]
        return func(*args)

    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync_inline)
    app.dependency_overrides[get_session] = override_get_session
    test_client = SameThreadTestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.pop(get_session, None)


__all__ = ["FakeDispatcher", "QueueModel", "TaskModel"]
