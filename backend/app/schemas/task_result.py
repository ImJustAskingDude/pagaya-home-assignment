from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import TaskStatus, TaskType


class TaskResultRead(BaseModel):
    id: int
    task_id: int
    queue_id: int
    type: TaskType
    status: TaskStatus
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
