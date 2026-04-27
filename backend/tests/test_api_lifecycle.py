from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel


def create_queue(client: TestClient, name: str = "default") -> dict[str, Any]:
    response = client.post("/api/queues", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_task(
    client: TestClient,
    queue_id: int,
    payload: dict[str, Any] | None = None,
    max_attempts: int = 1,
) -> dict[str, Any]:
    response = client.post(
        "/api/tasks",
        json={
            "queue_id": queue_id,
            "type": "echo",
            "payload": payload or {"message": "hello"},
            "max_attempts": max_attempts,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_queue_crud_lists_with_total_count_and_blocks_active_delete(client: TestClient) -> None:
    alpha = create_queue(client, " alpha ")
    beta = create_queue(client, "beta")

    assert alpha["name"] == " alpha "

    list_response = client.get("/api/queues", params={"order_by": "name", "limit": 1})
    assert list_response.status_code == 200
    assert list_response.headers["X-Total-Count"] == "2"
    assert list_response.json()["total"] == 2
    assert [queue["name"] for queue in list_response.json()["items"]] == [" alpha "]

    many_response = client.get(
        "/api/queues",
        params={"id__in": f"{alpha['id']},{beta['id']}", "order_by": "id"},
    )
    assert many_response.status_code == 200
    assert many_response.json()["total"] == 2

    name_filter_response = client.get("/api/queues", params={"name": "lph"})
    assert name_filter_response.status_code == 200
    assert name_filter_response.json()["total"] == 1
    assert name_filter_response.json()["items"][0]["id"] == alpha["id"]

    unknown_filter_response = client.get("/api/queues", params={"not_a_filter": "value"})
    assert unknown_filter_response.status_code == 200
    assert unknown_filter_response.json()["total"] == 2

    update_response = client.put(f"/api/queues/{alpha['id']}", json={"name": " critical "})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == " critical "

    duplicate_response = client.post("/api/queues", json={"name": " critical "})
    assert duplicate_response.status_code == 409

    task = create_task(client, alpha["id"])
    blocked_delete = client.delete(f"/api/queues/{alpha['id']}")
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["detail"] == "Cannot delete a queue with queued or running tasks"

    cancel_response = client.post(f"/api/tasks/{task['id']}/cancel")
    assert cancel_response.status_code == 200

    delete_response = client.delete(f"/api/queues/{alpha['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["name"] == " critical "

    missing_response = client.get(f"/api/queues/{alpha['id']}")
    assert missing_response.status_code == 404

    remaining_response = client.get("/api/queues")
    assert remaining_response.json()["items"][0]["id"] == beta["id"]


def test_task_create_list_cancel_and_delete_flow(client: TestClient, dispatcher: Any) -> None:
    queue = create_queue(client)

    task = create_task(client, queue["id"], max_attempts=3)

    assert task["status"] == TaskStatus.QUEUED.value
    assert task["queue_id"] == queue["id"]
    assert task["payload"] == {"message": "hello"}
    assert task["max_attempts"] == 3
    assert task["celery_task_id"] == f"celery-{task['id']}-1"
    assert dispatcher.enqueued == [task["id"]]

    get_response = client.get(f"/api/tasks/{task['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == task["id"]

    list_response = client.get(
        "/api/tasks",
        params={
            "queue_id": queue["id"],
            "status": TaskStatus.QUEUED.value,
            "type": "echo",
        },
    )
    assert list_response.status_code == 200
    assert list_response.headers["X-Total-Count"] == "1"
    assert list_response.json()["total"] == 1
    assert [item["id"] for item in list_response.json()["items"]] == [task["id"]]

    react_admin_large_page = client.get(
        "/api/tasks",
        params={"limit": 1000, "order_by": "-created_at"},
    )
    assert react_admin_large_page.status_code == 200
    assert react_admin_large_page.json()["total"] == 1

    invalid_filter = client.get("/api/tasks", params={"status": "not-a-status"})
    assert invalid_filter.status_code == 422

    invalid_sort = client.get("/api/tasks", params={"order_by": "not_a_field"})
    assert invalid_sort.status_code == 422

    unknown_filter = client.get("/api/tasks", params={"not_a_filter": "value"})
    assert unknown_filter.status_code == 200
    assert unknown_filter.json()["total"] == 1

    active_delete = client.delete(f"/api/tasks/{task['id']}")
    assert active_delete.status_code == 409
    assert active_delete.json()["detail"] == "Cancel active tasks before deleting them"

    cancel_response = client.post(f"/api/tasks/{task['id']}/cancel")
    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == TaskStatus.CANCELLED.value
    assert cancelled["cancel_requested_at"] is not None
    assert cancelled["finished_at"] is not None
    assert dispatcher.revoked == [task["celery_task_id"]]

    delete_response = client.delete(f"/api/tasks/{task['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == task["id"]

    missing_response = client.get(f"/api/tasks/{task['id']}")
    assert missing_response.status_code == 404


def test_retry_rejects_active_tasks_and_resets_failed_task_for_new_dispatch(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    task = create_task(client, queue["id"])

    conflict_response = client.post(f"/api/tasks/{task['id']}/retry")
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == "Only failed or cancelled tasks can be retried"

    now = datetime.now(timezone.utc)
    task_model = db_session.get(TaskModel, task["id"])
    assert task_model is not None
    task_model.status = TaskStatus.FAILED.value
    task_model.result = {"partial": True}
    task_model.error = "handler failed"
    task_model.attempts = 2
    task_model.started_at = now
    task_model.finished_at = now
    task_model.cancel_requested_at = now
    db_session.commit()

    retry_response = client.post(f"/api/tasks/{task['id']}/retry")
    assert retry_response.status_code == 200
    retried = retry_response.json()
    assert retried["status"] == TaskStatus.QUEUED.value
    assert retried["celery_task_id"] == f"celery-{task['id']}-2"
    assert retried["result"] is None
    assert retried["error"] is None
    assert retried["attempts"] == 0
    assert retried["started_at"] is None
    assert retried["finished_at"] is None
    assert retried["cancel_requested_at"] is None
    assert dispatcher.enqueued == [task["id"], task["id"]]


def test_create_task_dispatch_failure_returns_503_and_persists_failed_metadata(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    dispatcher.enqueue_errors.append(RuntimeError("redis offline"))

    response = client.post(
        "/api/tasks",
        json={
            "queue_id": queue["id"],
            "type": "echo",
            "payload": {"message": "hello"},
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Task could not be dispatched"

    task = db_session.scalars(select(TaskModel)).one()
    assert task.status == TaskStatus.FAILED.value
    assert task.celery_task_id is None
    assert task.error == "Dispatch failed: redis offline"
    assert task.finished_at is not None


def test_retry_dispatch_failure_returns_503_and_marks_task_failed(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    task = create_task(client, queue["id"])

    task_model = db_session.get(TaskModel, task["id"])
    assert task_model is not None
    task_model.status = TaskStatus.CANCELLED.value
    task_model.finished_at = datetime.now(timezone.utc)
    db_session.commit()

    dispatcher.enqueue_errors.append(RuntimeError("broker unavailable"))
    response = client.post(f"/api/tasks/{task['id']}/retry")

    assert response.status_code == 503
    assert response.json()["detail"] == "Task could not be dispatched"

    db_session.refresh(task_model)
    assert task_model.status == TaskStatus.FAILED.value
    assert task_model.celery_task_id is None
    assert task_model.error == "Dispatch failed: broker unavailable"
    assert task_model.finished_at is not None


def test_missing_resources_return_404(client: TestClient) -> None:
    assert client.get("/api/queues/999").status_code == 404
    assert client.get("/api/tasks/999").status_code == 404

    response = client.post(
        "/api/tasks",
        json={
            "queue_id": 999,
            "type": "echo",
            "payload": {"message": "hello"},
        },
    )
    assert response.status_code == 404
