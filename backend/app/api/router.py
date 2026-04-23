from fastapi import APIRouter

from app.api.queues import router as queues_router
from app.api.tasks import router as tasks_router

api_router = APIRouter(prefix="/api")
api_router.include_router(queues_router)
api_router.include_router(tasks_router)

