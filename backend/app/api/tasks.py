from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import raise_http_error
from app.core.database import get_session
from app.schemas.common import ListResponse
from app.schemas.task import TaskCreate, TaskRead
from app.services.errors import ConflictError, DispatchError, NotFoundError
from app.services.query import parse_filters
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=ListResponse[TaskRead])
def list_tasks(
    response: Response,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="id"),
    order: str = Query(default="ASC"),
    filter: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ListResponse[TaskRead]:
    items, total = TaskService(session).list(
        offset=offset,
        limit=limit,
        sort=sort,
        order=order,
        filters=parse_filters(filter),
    )
    response.headers["X-Total-Count"] = str(total)
    return ListResponse(items=items, total=total)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, session: Session = Depends(get_session)) -> TaskRead:
    try:
        return TaskService(session).create(payload)
    except (DispatchError, NotFoundError) as error:
        raise_http_error(error)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    try:
        return TaskService(session).get(task_id)
    except NotFoundError as error:
        raise_http_error(error)


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    try:
        return TaskService(session).cancel(task_id)
    except NotFoundError as error:
        raise_http_error(error)


@router.post("/{task_id}/retry", response_model=TaskRead)
def retry_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    try:
        return TaskService(session).retry(task_id)
    except (ConflictError, DispatchError, NotFoundError) as error:
        raise_http_error(error)


@router.delete("/{task_id}", response_model=TaskRead)
def delete_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    try:
        return TaskService(session).delete(task_id)
    except (ConflictError, NotFoundError) as error:
        raise_http_error(error)
