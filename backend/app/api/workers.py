from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import raise_http_error
from app.schemas.common import ListResponse
from app.schemas.worker import WorkerRead
from app.services.errors import DispatchError
from app.services.workers import WorkerService

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("", response_model=ListResponse[WorkerRead])
def list_workers(
    response: Response,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 25,
    order_by: Annotated[list[str] | None, Query()] = None,
) -> ListResponse[WorkerRead]:
    try:
        items, total = WorkerService().list(
            offset=offset,
            limit=limit,
            order_by=order_by or ["name"],
        )
    except DispatchError as error:
        raise_http_error(error)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    response.headers["X-Total-Count"] = str(total)
    return ListResponse(items=items, total=total)
