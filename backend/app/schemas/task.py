from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import TaskStatus, TaskType


class EchoPayload(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class WaitPayload(BaseModel):
    seconds: float = Field(gt=0, le=60)


class ComputeHashPayload(BaseModel):
    value: str = Field(min_length=1, max_length=100_000)


class RandomFailPayload(BaseModel):
    probability: float = Field(ge=0, le=1)


class CountPrimesPayload(BaseModel):
    n: int = Field(ge=0, le=200_000)


PAYLOAD_SCHEMAS: dict[TaskType, type[BaseModel]] = {
    TaskType.ECHO: EchoPayload,
    TaskType.WAIT: WaitPayload,
    TaskType.COMPUTE_HASH: ComputeHashPayload,
    TaskType.RANDOM_FAIL: RandomFailPayload,
    TaskType.COUNT_PRIMES: CountPrimesPayload,
}


class TaskRead(BaseModel):
    id: int
    queue_id: int
    celery_task_id: str | None
    type: str
    payload: dict[str, Any]
    status: TaskStatus
    result: dict[str, Any] | None
    error: str | None
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


def normalize_payload(task_type: TaskType, payload: dict[str, Any]) -> dict[str, Any]:
    schema = PAYLOAD_SCHEMAS[task_type]
    return schema.model_validate(payload).model_dump()


class TaskCreate(BaseModel):
    queue_id: int
    type: TaskType
    payload: dict[str, Any]
    max_attempts: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def validate_payload_for_type(self) -> "TaskCreate":
        self.payload = normalize_payload(self.type, self.payload)
        return self
