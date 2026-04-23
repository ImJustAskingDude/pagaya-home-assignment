from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TaskStatus
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.queue import QueueModel


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    queue_id: Mapped[int] = mapped_column(
        ForeignKey("queues.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        init=False,
        default=None,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        init=False,
        default=TaskStatus.QUEUED.value,
        index=True,
        nullable=False,
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, init=False, default=None)
    error: Mapped[str | None] = mapped_column(Text, init=False, default=None)
    attempts: Mapped[int] = mapped_column(init=False, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        server_default=func.now(),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default=None,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default=None,
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default=None,
    )

    queue: Mapped["QueueModel"] = relationship(init=False, back_populates="tasks")
