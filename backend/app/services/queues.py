from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.queue import QueueModel
from app.repositories.filters import QueueFilter
from app.repositories.queues import QueueRepository
from app.schemas.queue import QueueCreate, QueueUpdate
from app.services.errors import ConflictError, NotFoundError


class QueueService:
    def __init__(self, session: Session) -> None:
        self.queues = QueueRepository(session)

    def list(
        self,
        offset: int,
        limit: int,
        filters: QueueFilter,
    ) -> tuple[list[QueueModel], int]:
        return self.queues.list(offset=offset, limit=limit, filters=filters)

    def get(self, queue_id: int) -> QueueModel:
        queue = self.queues.get(queue_id)
        if queue is None:
            raise NotFoundError("Queue not found")
        return queue

    def create(self, data: QueueCreate) -> QueueModel:
        queue = QueueModel(name=data.name.strip())
        try:
            return self.queues.add(queue)
        except IntegrityError as exc:
            self.queues.rollback()
            raise ConflictError("Queue name already exists") from exc

    def update(self, queue_id: int, data: QueueUpdate) -> QueueModel:
        queue = self.get(queue_id)
        queue.name = data.name.strip()
        try:
            return self.queues.save(queue)
        except IntegrityError as exc:
            self.queues.rollback()
            raise ConflictError("Queue name already exists") from exc

    def delete(self, queue_id: int) -> QueueModel:
        queue = self.get(queue_id)
        if self.queues.count_active_tasks(queue_id):
            raise ConflictError("Cannot delete a queue with queued or running tasks")

        return self.queues.delete(queue)
