import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.queue import QueueCreate
from app.schemas.task import TaskCreate, WaitTaskCreate

TASK_CREATE_ADAPTER = TypeAdapter(TaskCreate)


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


def test_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        TASK_CREATE_ADAPTER.validate_python(
            {
                "queue_id": 1,
                "type": "wait",
                "payload": {"seconds": 0},
            }
        )
