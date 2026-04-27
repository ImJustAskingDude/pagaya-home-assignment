from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.api.dependencies import raise_http_error
from app.core.database import get_session
from app.repositories.filters import TaskResultFilter
from app.schemas.common import ListResponse
from app.schemas.task_result import TaskResultRead
from app.services.errors import NotFoundError
from app.services.task_results import TaskResultService

router = APIRouter(prefix="/task-results", tags=["task-results"])


@router.get("", response_model=ListResponse[TaskResultRead])
def list_task_results(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    filters: Annotated[TaskResultFilter, FilterDepends(TaskResultFilter)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 25,
) -> ListResponse[TaskResultRead]:
    items, total = TaskResultService(session).list(
        offset=offset,
        limit=limit,
        filters=filters,
    )
    response.headers["X-Total-Count"] = str(total)
    return ListResponse(items=items, total=total)


@router.get("/{task_result_id}", response_model=TaskResultRead)
def get_task_result(task_result_id: int, session: Annotated[Session, Depends(get_session)]) -> TaskResultRead:
    try:
        return TaskResultService(session).get(task_result_id)
    except NotFoundError as error:
        raise_http_error(error)
