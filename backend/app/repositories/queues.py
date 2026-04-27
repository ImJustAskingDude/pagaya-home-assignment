from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ACTIVE_STATUSES
from app.models.queue import QueueModel
from app.models.task import TaskModel
from app.repositories.filters import QueueFilter


class QueueRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        offset: int,
        limit: int,
        filters: QueueFilter,
    ) -> tuple[list[QueueModel], int]:
        statement = filters.filter(select(QueueModel))
        count_statement = filters.filter(select(func.count()).select_from(QueueModel))

        total = self.session.scalar(count_statement) or 0
        items = self.session.scalars(filters.sort(statement).offset(offset).limit(limit)).all()
        return list(items), total

    def get(self, queue_id: int) -> QueueModel | None:
        return self.session.get(QueueModel, queue_id)

    def add(self, queue: QueueModel) -> QueueModel:
        self.session.add(queue)
        self.session.commit()
        self.session.refresh(queue)
        return queue

    def save(self, queue: QueueModel) -> QueueModel:
        self.session.commit()
        self.session.refresh(queue)
        return queue

    def delete(self, queue: QueueModel) -> QueueModel:
        self.session.delete(queue)
        self.session.commit()
        return queue

    def count_active_tasks(self, queue_id: int) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(TaskModel)
                .where(TaskModel.queue_id == queue_id, TaskModel.status.in_(ACTIVE_STATUSES))
            )
            or 0
        )

    def rollback(self) -> None:
        self.session.rollback()
