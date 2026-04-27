from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.api.dependencies import raise_http_error
from app.core.database import get_session
from app.schemas.common import ListResponse
from app.schemas.queue import QueueCreate, QueueRead, QueueUpdate
from app.services.errors import ConflictError, NotFoundError
from app.services.query import QueueFilter
from app.services.queues import QueueService

router = APIRouter(prefix="/queues", tags=["queues"])


@router.get("", response_model=ListResponse[QueueRead])
def list_queues(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    filters: Annotated[QueueFilter, FilterDepends(QueueFilter)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 25,
) -> ListResponse[QueueRead]:
    items, total = QueueService(session).list(
        offset=offset,
        limit=limit,
        filters=filters,
    )
    response.headers["X-Total-Count"] = str(total)
    return ListResponse(items=items, total=total)


@router.post("", response_model=QueueRead, status_code=201)
def create_queue(
    payload: QueueCreate,
    session: Annotated[Session, Depends(get_session)],
) -> QueueRead:
    try:
        return QueueService(session).create(payload)
    except ConflictError as error:
        raise_http_error(error)


@router.get("/{queue_id}", response_model=QueueRead)
def get_queue(queue_id: int, session: Annotated[Session, Depends(get_session)]) -> QueueRead:
    try:
        return QueueService(session).get(queue_id)
    except NotFoundError as error:
        raise_http_error(error)


@router.put("/{queue_id}", response_model=QueueRead)
def update_queue(
    queue_id: int,
    payload: QueueUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> QueueRead:
    try:
        return QueueService(session).update(queue_id, payload)
    except (ConflictError, NotFoundError) as error:
        raise_http_error(error)


@router.delete("/{queue_id}", response_model=QueueRead)
def delete_queue(queue_id: int, session: Annotated[Session, Depends(get_session)]) -> QueueRead:
    try:
        return QueueService(session).delete(queue_id)
    except (ConflictError, NotFoundError) as error:
        raise_http_error(error)
