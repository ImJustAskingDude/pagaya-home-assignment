from typing import Any

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.task_execution import TaskExecutionService


@celery_app.task(bind=True, name="tasks.execute")
def execute_task(self, task_id: int) -> dict[str, Any]:
    with SessionLocal() as session:
        return TaskExecutionService(session, retry=self.retry).execute(task_id)
