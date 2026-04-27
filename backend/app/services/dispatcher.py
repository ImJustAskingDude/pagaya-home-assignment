from collections.abc import Sequence
from typing import Any, Protocol, cast

from app.celery_app import celery_app
from app.task_handlers.jobs import execute_task


class AsyncResultLike(Protocol):
    @property
    def id(self) -> str: ...


class ApplyAsyncTask(Protocol):
    def apply_async(
        self,
        args: Sequence[Any] | None = None,
        **options: Any,
    ) -> AsyncResultLike: ...


class CeleryControl(Protocol):
    def revoke(
        self,
        task_id: str | Sequence[str],
        destination: Sequence[str] | None = None,
        terminate: bool = False,
        signal: str = "SIGTERM",
        **kwargs: Any,
    ) -> object: ...


class CeleryDispatcher:
    def __init__(self) -> None:
        self.execute_task = cast(ApplyAsyncTask, execute_task)
        self.control = cast(CeleryControl, celery_app.control)

    def enqueue(self, task_id: int) -> str:
        async_result = self.execute_task.apply_async(args=(task_id,))
        return async_result.id

    def revoke(self, celery_task_id: str) -> None:
        self.control.revoke(celery_task_id, terminate=False)


dispatcher = CeleryDispatcher()
