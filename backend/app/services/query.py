from typing import Literal

from fastapi_filter.contrib.sqlalchemy import Filter

from app.core.enums import TaskStatus, TaskType
from app.models.queue import QueueModel
from app.models.task import TaskModel

TaskOrderField = Literal[
    "id",
    "+id",
    "-id",
    "queue_id",
    "+queue_id",
    "-queue_id",
    "type",
    "+type",
    "-type",
    "status",
    "+status",
    "-status",
    "attempts",
    "+attempts",
    "-attempts",
    "created_at",
    "+created_at",
    "-created_at",
    "started_at",
    "+started_at",
    "-started_at",
    "finished_at",
    "+finished_at",
    "-finished_at",
]

QueueOrderField = Literal[
    "id",
    "+id",
    "-id",
    "name",
    "+name",
    "-name",
    "created_at",
    "+created_at",
    "-created_at",
    "updated_at",
    "+updated_at",
    "-updated_at",
]


class TaskFilter(Filter):
    id__in: list[int] | None = None
    queue_id: int | None = None
    status: TaskStatus | None = None
    type: TaskType | None = None
    order_by: list[TaskOrderField] = ["id"]

    class Constants(Filter.Constants):
        model = TaskModel


class QueueFilter(Filter):
    id__in: list[int] | None = None
    name: str | None = None
    order_by: list[QueueOrderField] = ["id"]

    class Constants(Filter.Constants):
        model = QueueModel
        search_field_name = "name"
        search_model_fields = ["name"]
