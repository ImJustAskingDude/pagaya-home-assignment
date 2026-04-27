from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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


class JsonTransformPayload(BaseModel):
    input: dict[str, Any]
    select_keys: list[str] | None = Field(default=None, min_length=1, max_length=100)
    rename_keys: dict[str, str] = Field(default_factory=dict, max_length=100)


class TaskReadBase(BaseModel):
    id: int
    queue_id: int
    celery_task_id: str | None
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


class EchoTaskRead(TaskReadBase):
    type: Literal[TaskType.ECHO]
    payload: EchoPayload


class WaitTaskRead(TaskReadBase):
    type: Literal[TaskType.WAIT]
    payload: WaitPayload


class ComputeHashTaskRead(TaskReadBase):
    type: Literal[TaskType.COMPUTE_HASH]
    payload: ComputeHashPayload


class RandomFailTaskRead(TaskReadBase):
    type: Literal[TaskType.RANDOM_FAIL]
    payload: RandomFailPayload


class CountPrimesTaskRead(TaskReadBase):
    type: Literal[TaskType.COUNT_PRIMES]
    payload: CountPrimesPayload


class JsonTransformTaskRead(TaskReadBase):
    type: Literal[TaskType.JSON_TRANSFORM]
    payload: JsonTransformPayload


TaskRead = Annotated[
    (
        EchoTaskRead
        | WaitTaskRead
        | ComputeHashTaskRead
        | RandomFailTaskRead
        | CountPrimesTaskRead
        | JsonTransformTaskRead
    ),
    Field(discriminator="type"),
]


class TaskCreateBase(BaseModel):
    queue_id: int
    max_attempts: int = Field(default=1, ge=1, le=10)


class EchoTaskCreate(TaskCreateBase):
    type: Literal[TaskType.ECHO]
    payload: EchoPayload


class WaitTaskCreate(TaskCreateBase):
    type: Literal[TaskType.WAIT]
    payload: WaitPayload


class ComputeHashTaskCreate(TaskCreateBase):
    type: Literal[TaskType.COMPUTE_HASH]
    payload: ComputeHashPayload


class RandomFailTaskCreate(TaskCreateBase):
    type: Literal[TaskType.RANDOM_FAIL]
    payload: RandomFailPayload


class CountPrimesTaskCreate(TaskCreateBase):
    type: Literal[TaskType.COUNT_PRIMES]
    payload: CountPrimesPayload


class JsonTransformTaskCreate(TaskCreateBase):
    type: Literal[TaskType.JSON_TRANSFORM]
    payload: JsonTransformPayload


TaskCreate = Annotated[
    (
        EchoTaskCreate
        | WaitTaskCreate
        | ComputeHashTaskCreate
        | RandomFailTaskCreate
        | CountPrimesTaskCreate
        | JsonTransformTaskCreate
    ),
    Field(discriminator="type"),
]
