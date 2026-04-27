from fastapi_filter.contrib.sqlalchemy import Filter

from app.core.enums import TaskStatus, TaskType
from app.models.queue import QueueModel
from app.models.task import TaskModel
from app.models.task_result import TaskResultModel


class TaskFilter(Filter):
    id__in: list[int] | None = None
    queue_id: int | None = None
    status: TaskStatus | None = None
    type: TaskType | None = None
    # Let fastapi-filter validate sorting against SQLAlchemy model attributes.
    # This keeps the demo API flexible without maintaining a separate allowlist.
    order_by: list[str] = ["id"]

    class Constants(Filter.Constants):
        model = TaskModel


class QueueFilter(Filter):
    id__in: list[int] | None = None
    name: str | None = None
    # Let fastapi-filter validate sorting against SQLAlchemy model attributes.
    # This keeps the demo API flexible without maintaining a separate allowlist.
    order_by: list[str] = ["id"]

    class Constants(Filter.Constants):
        model = QueueModel
        search_field_name = "name"
        search_model_fields = ["name"]


class TaskResultFilter(Filter):
    id__in: list[int] | None = None
    task_id: int | None = None
    queue_id: int | None = None
    status: TaskStatus | None = None
    type: TaskType | None = None
    # Let fastapi-filter validate sorting against SQLAlchemy model attributes.
    # This keeps the demo API flexible without maintaining a separate allowlist.
    order_by: list[str] = ["id"]

    class Constants(Filter.Constants):
        model = TaskResultModel
