from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ACTIVE_STATUSES
from app.models.queue import QueueModel
from app.models.task import TaskModel
from app.schemas.queue import QueueCreate, QueueUpdate
from app.services.errors import ConflictError, NotFoundError
from app.services.query import QueueFilter


class QueueService:
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

    def get(self, queue_id: int) -> QueueModel:
        queue = self.session.get(QueueModel, queue_id)
        if queue is None:
            raise NotFoundError("Queue not found")
        return queue

    def create(self, data: QueueCreate) -> QueueModel:
        queue = QueueModel(name=data.name.strip())
        self.session.add(queue)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Queue name already exists") from exc
        self.session.refresh(queue)
        return queue

    def update(self, queue_id: int, data: QueueUpdate) -> QueueModel:
        queue = self.get(queue_id)
        queue.name = data.name.strip()
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Queue name already exists") from exc
        self.session.refresh(queue)
        return queue

    def delete(self, queue_id: int) -> QueueModel:
        queue = self.get(queue_id)
        active_count = self.session.scalar(
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.queue_id == queue_id, TaskModel.status.in_(ACTIVE_STATUSES))
        )
        if active_count:
            raise ConflictError("Cannot delete a queue with queued or running tasks")

        self.session.delete(queue)
        self.session.commit()
        return queue
