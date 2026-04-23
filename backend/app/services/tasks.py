from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ACTIVE_STATUSES, TaskStatus
from app.models.queue import QueueModel
from app.models.task import TaskModel
from app.schemas.task import TaskCreate, normalize_payload
from app.services.dispatcher import dispatcher
from app.services.errors import ConflictError, DispatchError, NotFoundError

TASK_SORT_FIELDS = {
    "id": TaskModel.id,
    "queue_id": TaskModel.queue_id,
    "type": TaskModel.type,
    "status": TaskModel.status,
    "attempts": TaskModel.attempts,
    "created_at": TaskModel.created_at,
    "started_at": TaskModel.started_at,
    "finished_at": TaskModel.finished_at,
}


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        offset: int,
        limit: int,
        sort: str,
        order: str,
        filters: dict[str, Any],
    ) -> tuple[list[TaskModel], int]:
        sort_column = TASK_SORT_FIELDS.get(sort, TaskModel.id)
        if order.upper() == "DESC":
            sort_column = sort_column.desc()

        statement = select(TaskModel)
        count_statement = select(func.count()).select_from(TaskModel)

        queue_id = filters.get("queue_id")
        status = filters.get("status")
        task_type = filters.get("type")
        ids = filters.get("ids")

        conditions = []
        if isinstance(ids, list) and ids:
            conditions.append(TaskModel.id.in_([int(task_id) for task_id in ids]))
        if queue_id:
            conditions.append(TaskModel.queue_id == int(queue_id))
        if status:
            conditions.append(TaskModel.status == str(status))
        if task_type:
            conditions.append(TaskModel.type == str(task_type))

        if conditions:
            statement = statement.where(*conditions)
            count_statement = count_statement.where(*conditions)

        total = self.session.scalar(count_statement) or 0
        items = self.session.scalars(statement.order_by(sort_column).offset(offset).limit(limit)).all()
        return list(items), total

    def get(self, task_id: int) -> TaskModel:
        task = self.session.get(TaskModel, task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def create(self, data: TaskCreate) -> TaskModel:
        queue = self.session.get(QueueModel, data.queue_id)
        if queue is None:
            raise NotFoundError("Queue not found")

        task = TaskModel(
            queue_id=data.queue_id,
            type=data.type.value,
            payload=normalize_payload(data.type, data.payload),
            max_attempts=data.max_attempts,
            status=TaskStatus.QUEUED.value,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            task.status = TaskStatus.FAILED.value
            task.error = f"Dispatch failed: {exc}"
            task.finished_at = datetime.now(timezone.utc)
            self.session.commit()
            raise DispatchError("Task could not be dispatched") from exc

        task.celery_task_id = celery_task_id
        self.session.commit()
        self.session.refresh(task)
        return task

    def cancel(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in ACTIVE_STATUSES:
            return task

        now = datetime.now(timezone.utc)
        task.cancel_requested_at = now
        if task.status == TaskStatus.QUEUED.value:
            task.status = TaskStatus.CANCELLED.value
            task.finished_at = now

        if task.celery_task_id:
            dispatcher.revoke(task.celery_task_id)

        self.session.commit()
        self.session.refresh(task)
        return task

    def retry(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}:
            raise ConflictError("Only failed or cancelled tasks can be retried")

        task.status = TaskStatus.QUEUED.value
        task.result = None
        task.error = None
        task.attempts = 0
        task.started_at = None
        task.finished_at = None
        task.cancel_requested_at = None
        task.celery_task_id = None
        self.session.commit()
        self.session.refresh(task)

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            task.status = TaskStatus.FAILED.value
            task.error = f"Dispatch failed: {exc}"
            task.finished_at = datetime.now(timezone.utc)
            self.session.commit()
            raise DispatchError("Task could not be dispatched") from exc

        task.celery_task_id = celery_task_id
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status in ACTIVE_STATUSES:
            raise ConflictError("Cancel active tasks before deleting them")
        self.session.delete(task)
        self.session.commit()
        return task
