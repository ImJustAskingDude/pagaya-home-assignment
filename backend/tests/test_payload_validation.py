import pytest
from pydantic import ValidationError

from app.core.enums import TaskType
from app.schemas.task import normalize_payload


def test_normalizes_valid_payload() -> None:
    assert normalize_payload(TaskType.ECHO, {"message": "hello"}) == {"message": "hello"}


def test_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        normalize_payload(TaskType.WAIT, {"seconds": 0})

