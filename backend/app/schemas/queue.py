from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueueBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Queue name cannot be blank")
        return cleaned


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
