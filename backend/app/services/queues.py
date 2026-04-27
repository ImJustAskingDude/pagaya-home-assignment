from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.queue import QueueModel
from app.repositories.filters import QueueFilter
from app.repositories.queues import QueueRepository
from app.schemas.queue import QueueCreate, QueueUpdate
from app.services.errors import ConflictError, NotFoundError
from app.services.unit_of_work import UnitOfWork


class QueueService:
    def __init__(self, session: Session) -> None:
        self.unit_of_work = UnitOfWork(session)
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
        queue = QueueModel(name=data.name)
        try:
            with self.unit_of_work:
                self.queues.add(queue)
        except IntegrityError as exc:
            raise ConflictError("Queue name already exists") from exc

        self.unit_of_work.refresh(queue)
        return queue

    def update(self, queue_id: int, data: QueueUpdate) -> QueueModel:
        queue = self.get(queue_id)
        try:
            with self.unit_of_work:
                queue.name = data.name
                self.queues.save(queue)
        except IntegrityError as exc:
            raise ConflictError("Queue name already exists") from exc

        self.unit_of_work.refresh(queue)
        return queue

    def delete(self, queue_id: int) -> QueueModel:
        queue = self.get(queue_id)
        if self.queues.count_active_tasks(queue_id):
            raise ConflictError("Cannot delete a queue with queued or running tasks")

        with self.unit_of_work:
            self.queues.delete(queue)
        return queue
