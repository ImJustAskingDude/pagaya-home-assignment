from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def clean_queue_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Queue name cannot be blank")
    return cleaned


QueueName = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(clean_queue_name)]


class QueueBase(BaseModel):
    name: QueueName


class QueueCreate(QueueBase):
    pass


class QueueUpdate(QueueBase):
    pass


class QueueRead(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
