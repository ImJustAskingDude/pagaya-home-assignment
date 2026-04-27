from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import TaskModel
from app.models.task_result import TaskResultModel
from app.repositories.filters import TaskResultFilter


class TaskResultRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        offset: int,
        limit: int,
        filters: TaskResultFilter,
    ) -> tuple[list[TaskResultModel], int]:
        statement = filters.filter(select(TaskResultModel))
        count_statement = filters.filter(select(func.count()).select_from(TaskResultModel))

        total = self.session.scalar(count_statement) or 0
        items = self.session.scalars(filters.sort(statement).offset(offset).limit(limit)).all()
        return list(items), total

    def get(self, task_result_id: int) -> TaskResultModel | None:
        return self.session.get(TaskResultModel, task_result_id)

    def add(self, task_result: TaskResultModel) -> TaskResultModel:
        self.session.add(task_result)
        return task_result

    def add_from_task(self, task: TaskModel) -> TaskResultModel:
        task_result = TaskResultModel(
            task_id=task.id,
            queue_id=task.queue_id,
            type=task.type,
            status=task.status,
            result=task.result,
            error=task.error,
        )
        return self.add(task_result)
