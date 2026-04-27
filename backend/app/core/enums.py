from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    ECHO = "echo"
    WAIT = "wait"
    COMPUTE_HASH = "compute_hash"
    RANDOM_FAIL = "random_fail"
    COUNT_PRIMES = "count_primes"
    JSON_TRANSFORM = "json_transform"
    BATCH_FANOUT = "batch_fanout"


ACTIVE_STATUSES = {TaskStatus.QUEUED.value, TaskStatus.RUNNING.value}
TERMINAL_STATUSES = {TaskStatus.SUCCEEDED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}
