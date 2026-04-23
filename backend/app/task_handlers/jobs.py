from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.task_handlers.cancellation import TaskCancelled
from app.task_handlers.registry import get_handler


@celery_app.task(bind=True, name="tasks.execute")
def execute_task(self, task_id: int) -> dict[str, Any]:
    with SessionLocal() as session:
        task = session.get(TaskModel, task_id)
        if task is None:
            return {"ignored": True, "reason": "task_not_found"}
        if task.status == TaskStatus.CANCELLED.value or task.cancel_requested_at is not None:
            _mark_cancelled(session, task)
            return {"cancelled": True}

        task.status = TaskStatus.RUNNING.value
        task.attempts += 1
        task.started_at = datetime.now(timezone.utc)
        task.finished_at = None
        task.error = None
        session.commit()

        try:
            handler = get_handler(task.type)
            result = handler(task.payload, lambda: _is_cancel_requested(session, task_id))
        except TaskCancelled:
            _mark_cancelled(session, task)
            return {"cancelled": True}
        except Exception as exc:
            return _handle_failure(self, session, task, exc)

        task.status = TaskStatus.SUCCEEDED.value
        task.result = result
        task.error = None
        task.finished_at = datetime.now(timezone.utc)
        session.commit()
        return result


def _is_cancel_requested(session: Session, task_id: int) -> bool:
    session.expire_all()
    task = session.get(TaskModel, task_id)
    return task is None or task.status == TaskStatus.CANCELLED.value or task.cancel_requested_at is not None


def _mark_cancelled(session: Session, task: TaskModel) -> None:
    task.status = TaskStatus.CANCELLED.value
    task.finished_at = datetime.now(timezone.utc)
    session.commit()


def _handle_failure(self, session: Session, task: TaskModel, exc: Exception) -> dict[str, Any]:
    task.error = str(exc)

    if task.attempts < task.max_attempts and task.cancel_requested_at is None:
        task.status = TaskStatus.QUEUED.value
        task.finished_at = None
        session.commit()
        raise self.retry(exc=exc, countdown=2, max_retries=task.max_attempts - 1)

    task.status = TaskStatus.FAILED.value
    task.finished_at = datetime.now(timezone.utc)
    session.commit()
    raise exc
