from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.models.task_result import TaskResultModel
from app.services.task_execution import TaskExecutionService


def create_queue(client: TestClient, name: str = "default") -> dict[str, Any]:
    response = client.post("/api/queues", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_task(
    client: TestClient,
    queue_id: int,
    task_type: str = "echo",
    payload: dict[str, Any] | None = None,
    max_attempts: int = 1,
) -> dict[str, Any]:
    response = client.post(
        "/api/tasks",
        json={
            "queue_id": queue_id,
            "type": task_type,
            "payload": payload or {"message": "hello"},
            "max_attempts": max_attempts,
        },
    )
    assert response.status_code == 201
    return response.json()


def fail_unexpected_retry(*, exc: Exception, countdown: int, max_retries: int) -> None:
    raise AssertionError("Celery retry was not expected in this test")


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

    initial_results = client.get("/api/task-results", params={"task_id": task["id"]})
    assert initial_results.status_code == 200
    assert initial_results.json()["total"] == 0

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

    invalid_result_sort = client.get("/api/task-results", params={"order_by": "not_a_field"})
    assert invalid_result_sort.status_code == 422

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

    cancelled_results = client.get("/api/task-results", params={"task_id": task["id"]})
    assert cancelled_results.status_code == 200
    assert cancelled_results.json()["total"] == 1
    cancelled_result = cancelled_results.json()["items"][0]
    assert cancelled_result["task_id"] == task["id"]
    assert cancelled_result["queue_id"] == queue["id"]
    assert cancelled_result["type"] == "echo"
    assert cancelled_result["status"] == TaskStatus.CANCELLED.value
    assert cancelled_result["result"] is None
    assert cancelled_result["error"] is None

    delete_response = client.delete(f"/api/tasks/{task['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == task["id"]

    missing_response = client.get(f"/api/tasks/{task['id']}")
    assert missing_response.status_code == 404


def test_retry_rejects_active_tasks_and_resets_finished_task_for_new_dispatch(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    task = create_task(client, queue["id"])

    conflict_response = client.post(f"/api/tasks/{task['id']}/retry")
    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == "Only finished tasks can be retried"

    now = datetime.now(timezone.utc)
    task_model = db_session.get(TaskModel, task["id"])
    assert task_model is not None
    task_model.status = TaskStatus.SUCCEEDED.value
    task_model.result = {"message": "done"}
    task_model.error = None
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


def test_task_results_preserve_each_finished_retry(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    task = create_task(client, queue["id"], payload={"message": "history"})

    service = TaskExecutionService(db_session, retry=fail_unexpected_retry)
    assert service.execute(task["id"]) == {"message": "history"}

    first_results = client.get("/api/task-results", params={"task_id": task["id"], "order_by": "id"})
    assert first_results.status_code == 200
    assert first_results.json()["total"] == 1
    assert first_results.json()["items"][0]["result"] == {"message": "history"}

    retry_response = client.post(f"/api/tasks/{task['id']}/retry")
    assert retry_response.status_code == 200
    assert dispatcher.enqueued == [task["id"], task["id"]]

    assert service.execute(task["id"]) == {"message": "history"}

    retry_results = client.get("/api/task-results", params={"task_id": task["id"], "order_by": "id"})
    assert retry_results.status_code == 200
    assert retry_results.json()["total"] == 2
    results = retry_results.json()["items"]
    assert [result["task_id"] for result in results] == [task["id"], task["id"]]
    assert [result["status"] for result in results] == [
        TaskStatus.SUCCEEDED.value,
        TaskStatus.SUCCEEDED.value,
    ]
    assert [result["result"] for result in results] == [
        {"message": "history"},
        {"message": "history"},
    ]


def test_json_transform_task_selects_and_renames_keys(
    client: TestClient,
    db_session: Session,
) -> None:
    queue = create_queue(client)
    task = create_task(
        client,
        queue["id"],
        task_type="json_transform",
        payload={
            "input": {"id": 7, "name": "alpha", "ignored": True},
            "select_keys": ["id", "name"],
            "rename_keys": {"id": "task_id"},
        },
    )

    result = TaskExecutionService(db_session, retry=fail_unexpected_retry).execute(task["id"])

    assert result == {"output": {"task_id": 7, "name": "alpha"}}


def test_batch_fanout_task_creates_and_dispatches_child_tasks(
    client: TestClient,
    db_session: Session,
    dispatcher: Any,
) -> None:
    queue = create_queue(client)
    task = create_task(
        client,
        queue["id"],
        task_type="batch_fanout",
        payload={
            "child_count": 3,
            "message_prefix": "batch",
            "child_max_attempts": 2,
        },
    )

    result = TaskExecutionService(
        db_session,
        retry=fail_unexpected_retry,
        task_dispatcher=dispatcher,
    ).execute(task["id"])

    child_ids = result["child_task_ids"]
    children = db_session.scalars(select(TaskModel).where(TaskModel.id.in_(child_ids)).order_by(TaskModel.id)).all()

    assert result == {"child_count": 3, "child_task_ids": child_ids}
    assert dispatcher.enqueued == [task["id"], *child_ids]
    assert [child.type for child in children] == ["echo", "echo", "echo"]
    assert [child.payload for child in children] == [
        {"message": "batch 1"},
        {"message": "batch 2"},
        {"message": "batch 3"},
    ]
    assert [child.max_attempts for child in children] == [2, 2, 2]
    assert all(child.celery_task_id for child in children)


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

    task_result = db_session.scalars(select(TaskResultModel)).one()
    assert task_result.task_id == task.id
    assert task_result.queue_id == queue["id"]
    assert task_result.type == "echo"
    assert task_result.status == TaskStatus.FAILED.value
    assert task_result.result is None
    assert task_result.error == "Dispatch failed: redis offline"


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

    task_result = db_session.scalars(select(TaskResultModel)).one()
    assert task_result.task_id == task["id"]
    assert task_result.status == TaskStatus.FAILED.value
    assert task_result.error == "Dispatch failed: broker unavailable"


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
