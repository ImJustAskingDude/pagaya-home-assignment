from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int


class QueryParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=1000)
    sort: str = "id"
    order: str = "ASC"
    filter: str | None = None

    model_config = ConfigDict(extra="forbid")
