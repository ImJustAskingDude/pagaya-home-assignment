import hashlib
import random
import time
from collections.abc import Callable
from typing import Any

from app.core.enums import TaskType
from app.task_handlers.cancellation import TaskCancelled

CancelCheck = Callable[[], bool]
TaskResult = dict[str, Any]
TaskHandler = Callable[[dict[str, Any], CancelCheck], TaskResult]


def _raise_if_cancelled(is_cancel_requested: CancelCheck) -> None:
    if is_cancel_requested():
        raise TaskCancelled()


def echo(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    _raise_if_cancelled(is_cancel_requested)
    return {"message": payload["message"]}


def wait(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    seconds = float(payload["seconds"])
    elapsed = 0.0
    while elapsed < seconds:
        _raise_if_cancelled(is_cancel_requested)
        step = min(0.5, seconds - elapsed)
        time.sleep(step)
        elapsed += step
    _raise_if_cancelled(is_cancel_requested)
    return {"waited_seconds": seconds}


def compute_hash(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    _raise_if_cancelled(is_cancel_requested)
    digest = hashlib.sha256(payload["value"].encode("utf-8")).hexdigest()
    return {"algorithm": "sha256", "digest": digest}


def random_fail(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    _raise_if_cancelled(is_cancel_requested)
    probability = float(payload["probability"])
    if random.random() < probability:
        raise RuntimeError(f"Random failure at probability {probability}")
    return {"succeeded": True, "probability": probability}


def count_primes(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    limit = int(payload["n"])
    count = 0
    for number in range(2, limit + 1):
        if number % 500 == 0:
            _raise_if_cancelled(is_cancel_requested)
        if _is_prime(number):
            count += 1
    _raise_if_cancelled(is_cancel_requested)
    return {"n": limit, "prime_count": count}


def json_transform(payload: dict[str, Any], is_cancel_requested: CancelCheck) -> TaskResult:
    input_data = payload["input"]
    select_keys = payload.get("select_keys")
    rename_keys = payload.get("rename_keys") or {}
    keys = select_keys if select_keys is not None else input_data.keys()

    output = {}
    for key in keys:
        _raise_if_cancelled(is_cancel_requested)
        if key in input_data:
            output[rename_keys.get(key, key)] = input_data[key]

    _raise_if_cancelled(is_cancel_requested)
    return {"output": output}


def _is_prime(number: int) -> bool:
    if number < 2:
        return False
    if number == 2:
        return True
    if number % 2 == 0:
        return False

    divisor = 3
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 2
    return True


HANDLERS: dict[str, TaskHandler] = {
    TaskType.ECHO.value: echo,
    TaskType.WAIT.value: wait,
    TaskType.COMPUTE_HASH.value: compute_hash,
    TaskType.RANDOM_FAIL.value: random_fail,
    TaskType.COUNT_PRIMES.value: count_primes,
    TaskType.JSON_TRANSFORM.value: json_transform,
}


def get_handler(task_type: str) -> TaskHandler:
    return HANDLERS[task_type]
