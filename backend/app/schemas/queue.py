from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# Use a non-whitespace pattern instead of StringConstraints(strip_whitespace=True)
# so validation rejects blank names without normalizing the user's input.
QueueName = Annotated[str, Field(min_length=1, max_length=120, pattern=r"\S")]


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
