from inspect import Parameter, signature

import pytest

from app.core.enums import TaskStatus
from app.models.queue import QueueModel
from app.models.task import TaskModel


def test_queue_model_constructor_is_keyword_only_and_application_owned() -> None:
    params = signature(QueueModel).parameters

    assert list(params) == ["name"]
    assert params["name"].kind is Parameter.KEYWORD_ONLY
    assert QueueModel(name="default").name == "default"

    with pytest.raises(TypeError):
        QueueModel("default")  # type: ignore[call-arg]


def test_task_model_constructor_is_keyword_only_and_application_owned() -> None:
    params = signature(TaskModel).parameters

    assert list(params) == ["queue_id", "type", "payload", "max_attempts"]
    assert all(param.kind is Parameter.KEYWORD_ONLY for param in params.values())
    assert params["max_attempts"].default == 1

    task = TaskModel(
        queue_id=1,
        type="echo",
        payload={"message": "hello"},
        max_attempts=3,
    )

    assert task.queue_id == 1
    assert task.type == "echo"
    assert task.payload == {"message": "hello"}
    assert task.max_attempts == 3
    assert task.status == TaskStatus.QUEUED.value
    assert task.attempts == 0
    assert task.celery_task_id is None
    assert task.result is None
    assert task.error is None

    with pytest.raises(TypeError):
        TaskModel(1, "echo", {"message": "hello"})  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        TaskModel(
            queue_id=1,
            type="echo",
            payload={"message": "hello"},
            status=TaskStatus.QUEUED.value,
        )
