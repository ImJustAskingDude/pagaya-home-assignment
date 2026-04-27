from sqlalchemy.orm import Session

from app.models.task_result import TaskResultModel
from app.repositories.filters import TaskResultFilter
from app.repositories.task_results import TaskResultRepository
from app.services.errors import NotFoundError


class TaskResultService:
    def __init__(self, session: Session) -> None:
        self.task_results = TaskResultRepository(session)

    def list(
        self,
        offset: int,
        limit: int,
        filters: TaskResultFilter,
    ) -> tuple[list[TaskResultModel], int]:
        return self.task_results.list(offset=offset, limit=limit, filters=filters)

    def get(self, task_result_id: int) -> TaskResultModel:
        task_result = self.task_results.get(task_result_id)
        if task_result is None:
            raise NotFoundError("Task result not found")
        return task_result
