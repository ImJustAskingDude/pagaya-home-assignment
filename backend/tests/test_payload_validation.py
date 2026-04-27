import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.queue import QueueCreate
from app.schemas.task import (
    BatchFanoutTaskCreate,
    EchoTaskRead,
    JsonTransformTaskCreate,
    TaskCreate,
    TaskRead,
    WaitTaskCreate,
)

TASK_CREATE_ADAPTER = TypeAdapter(TaskCreate)
TASK_READ_ADAPTER = TypeAdapter(TaskRead)


def test_queue_name_preserves_input_and_rejects_blank() -> None:
    assert QueueCreate(name=" alpha ").name == " alpha "

    with pytest.raises(ValidationError):
        QueueCreate(name="   ")


def test_discriminates_task_payload_by_type() -> None:
    task = TASK_CREATE_ADAPTER.validate_python(
        {
            "queue_id": 1,
            "type": "wait",
            "payload": {"seconds": 1},
        }
    )

    assert isinstance(task, WaitTaskCreate)
    assert task.payload.seconds == 1


def test_discriminates_json_transform_payload_by_type() -> None:
    task = TASK_CREATE_ADAPTER.validate_python(
        {
            "queue_id": 1,
            "type": "json_transform",
            "payload": {
                "input": {"id": 1, "name": "alpha", "ignored": True},
                "select_keys": ["id", "name"],
                "rename_keys": {"id": "task_id"},
            },
        }
    )

    assert isinstance(task, JsonTransformTaskCreate)
    assert task.payload.input == {"id": 1, "name": "alpha", "ignored": True}
    assert task.payload.select_keys == ["id", "name"]
    assert task.payload.rename_keys == {"id": "task_id"}


def test_discriminates_batch_fanout_payload_by_type() -> None:
    task = TASK_CREATE_ADAPTER.validate_python(
        {
            "queue_id": 1,
            "type": "batch_fanout",
            "payload": {
                "child_count": 3,
                "message_prefix": "batch",
                "child_max_attempts": 2,
            },
        }
    )

    assert isinstance(task, BatchFanoutTaskCreate)
    assert task.payload.child_count == 3
    assert task.payload.message_prefix == "batch"
    assert task.payload.child_max_attempts == 2


def test_discriminates_task_read_payload_by_type() -> None:
    task = TASK_READ_ADAPTER.validate_python(
        {
            "id": 1,
            "queue_id": 1,
            "celery_task_id": "celery-1-1",
            "type": "echo",
            "payload": {"message": "hello"},
            "status": "queued",
            "result": None,
            "error": None,
            "attempts": 0,
            "max_attempts": 1,
            "created_at": "2026-04-27T08:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "cancel_requested_at": None,
        }
    )

    assert isinstance(task, EchoTaskRead)
    assert task.payload.message == "hello"


def test_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        TASK_CREATE_ADAPTER.validate_python(
            {
                "queue_id": 1,
                "type": "wait",
                "payload": {"seconds": 0},
            }
        )
