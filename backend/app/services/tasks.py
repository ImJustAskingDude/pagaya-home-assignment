from sqlalchemy.orm import Session

from app.core.enums import ACTIVE_STATUSES, TERMINAL_STATUSES
from app.models.task import TaskModel
from app.repositories.filters import TaskFilter
from app.repositories.queues import QueueRepository
from app.repositories.task_results import TaskResultRepository
from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate
from app.services.dispatcher import dispatcher
from app.services.errors import ConflictError, DispatchError, NotFoundError
from app.services.unit_of_work import UnitOfWork


class TaskService:
    def __init__(self, session: Session) -> None:
        self.unit_of_work = UnitOfWork(session)
        self.queues = QueueRepository(session)
        self.task_results = TaskResultRepository(session)
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

        task = TaskModel(
            queue_id=data.queue_id,
            type=data.type.value,
            payload=data.payload.model_dump(),
            max_attempts=data.max_attempts,
        )
        with self.unit_of_work:
            self.tasks.add(task)
        self.unit_of_work.refresh(task)

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            with self.unit_of_work:
                task.mark_dispatch_failed(exc)
                self.task_results.add_from_task(task)
                self.tasks.save(task)
            raise DispatchError("Task could not be dispatched") from exc

        with self.unit_of_work:
            task.store_celery_task_id(celery_task_id)
            self.tasks.save(task)
        self.unit_of_work.refresh(task)
        return task

    def cancel(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in ACTIVE_STATUSES:
            return task

        with self.unit_of_work:
            task.request_cancel()
            if task.status not in ACTIVE_STATUSES:
                self.task_results.add_from_task(task)
            self.tasks.save(task)
        self.unit_of_work.refresh(task)

        if task.celery_task_id:
            dispatcher.revoke(task.celery_task_id)

        return task

    def retry(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status not in TERMINAL_STATUSES:
            raise ConflictError("Only finished tasks can be retried")

        with self.unit_of_work:
            task.reset_for_retry()
            self.tasks.save(task)
        self.unit_of_work.refresh(task)

        try:
            celery_task_id = dispatcher.enqueue(task.id)
        except Exception as exc:
            with self.unit_of_work:
                task.mark_dispatch_failed(exc)
                self.task_results.add_from_task(task)
                self.tasks.save(task)
            raise DispatchError("Task could not be dispatched") from exc

        with self.unit_of_work:
            task.store_celery_task_id(celery_task_id)
            self.tasks.save(task)
        self.unit_of_work.refresh(task)
        return task

    def delete(self, task_id: int) -> TaskModel:
        task = self.get(task_id)
        if task.status in ACTIVE_STATUSES:
            raise ConflictError("Cancel active tasks before deleting them")
        with self.unit_of_work:
            self.tasks.delete(task)
        return task
