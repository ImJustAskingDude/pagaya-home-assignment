from sqlalchemy.orm import Session

from app.core.enums import ACTIVE_STATUSES, TaskStatus
from app.models.task import TaskModel
from app.repositories.filters import TaskFilter
from app.repositories.queues import QueueRepository
from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate
from app.services.dispatcher import dispatcher
from app.services.errors import ConflictError, DispatchError, NotFoundError


class TaskService:
    def __init__(self, session: Session) -> None:
        self.queues = QueueRepository(session)
        self.tasks = TaskRepository(session)

    def list(
        self,
        offset: int,
        limit: int,
        filters: TaskFilter,
    ) -> tuple[list[TaskModel], int]:
        return self.tasks.list(offset=offset, limit=limit, filters=filters)

    def get(self, task_id: int) -> TaskModel:
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def create(self, data: TaskCreate) -> TaskModel:
        if self.queues.get(data.queue_id) is None:
            raise NotFoundError("Queue not found")

        task = self.tasks.add(
            TaskModel(
                queue_id=data.queue_id,
                type=data.type.value,
                payload=data.payload.model_dump(),
                max_attempts=data.max_attempts,
            )
        )

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            self.tasks.mark_dispatch_failed(task, exc)
            raise DispatchError("Task could not be dispatched") from exc

        return self.tasks.store_celery_task_id(task, celery_task_id)

    def cancel(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in ACTIVE_STATUSES:
            return task

        self.tasks.request_cancel(task)

        if task.celery_task_id:
            dispatcher.revoke(task.celery_task_id)

        return task

    def retry(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}:
            raise ConflictError("Only failed or cancelled tasks can be retried")

        self.tasks.reset_for_retry(task)

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            self.tasks.mark_dispatch_failed(task, exc)
            raise DispatchError("Task could not be dispatched") from exc

        return self.tasks.store_celery_task_id(task, celery_task_id)

    def delete(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status in ACTIVE_STATUSES:
            raise ConflictError("Cancel active tasks before deleting them")
        return self.tasks.delete(task)
