from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.repositories.filters import TaskFilter


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        offset: int,
        limit: int,
        filters: TaskFilter,
    ) -> tuple[list[TaskModel], int]:
        statement = filters.filter(select(TaskModel))
        count_statement = filters.filter(select(func.count()).select_from(TaskModel))

        total = self.session.scalar(count_statement) or 0
        items = self.session.scalars(filters.sort(statement).offset(offset).limit(limit)).all()
        return list(items), total

    def get(self, task_id: int) -> TaskModel | None:
        return self.session.get(TaskModel, task_id)

    def add(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        return task

    def delete(self, task: TaskModel) -> TaskModel:
        self.session.delete(task)
        return task

    def save(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        return task

    def cancellation_requested(self, task_id: int) -> bool:
        self.session.expire_all()
        task = self.session.get(TaskModel, task_id)
        return (
            task is None
            or task.status == TaskStatus.CANCELLED.value
            or task.cancel_requested_at is not None
        )
