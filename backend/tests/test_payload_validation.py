import pytest
from pydantic import ValidationError

from app.core.enums import TaskType
from app.schemas.queue import QueueCreate
from app.schemas.task import normalize_payload


def test_queue_name_is_trimmed_and_rejects_blank() -> None:
    assert QueueCreate(name=" alpha ").name == "alpha"

    with pytest.raises(ValidationError):
        QueueCreate(name="   ")


def test_normalizes_valid_payload() -> None:
    assert normalize_payload(TaskType.ECHO, {"message": "hello"}) == {"message": "hello"}


def test_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        normalize_payload(TaskType.WAIT, {"seconds": 0})
