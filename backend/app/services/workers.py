from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from app.celery_app import celery_app
from app.schemas.worker import WorkerRead
from app.services.errors import DispatchError


InspectionResponse = dict[str, Any]
InspectionListResponse = dict[str, list[Any]]


class CeleryInspect(Protocol):
    def ping(self) -> InspectionResponse | None: ...

    def stats(self) -> InspectionResponse | None: ...

    def active(self) -> InspectionListResponse | None: ...

    def reserved(self) -> InspectionListResponse | None: ...

    def scheduled(self) -> InspectionListResponse | None: ...

    def registered(self) -> InspectionListResponse | None: ...

    def active_queues(self) -> InspectionListResponse | None: ...


class CeleryInspectControl(Protocol):
    def inspect(self, timeout: float) -> CeleryInspect: ...


class WorkerInspector(Protocol):
    def snapshot(self) -> "WorkerInspection": ...


@dataclass(frozen=True)
class WorkerInspection:
    pings: InspectionResponse
    stats: InspectionResponse
    active: InspectionListResponse
    reserved: InspectionListResponse
    scheduled: InspectionListResponse
    registered: InspectionListResponse
    active_queues: InspectionListResponse


class CeleryWorkerInspector:
    def __init__(self) -> None:
        self.control = cast(CeleryInspectControl, celery_app.control)

    def snapshot(self) -> WorkerInspection:
        inspector = self.control.inspect(timeout=1.0)

        try:
            return WorkerInspection(
                pings=inspector.ping() or {},
                stats=inspector.stats() or {},
                active=inspector.active() or {},
                reserved=inspector.reserved() or {},
                scheduled=inspector.scheduled() or {},
                registered=inspector.registered() or {},
                active_queues=inspector.active_queues() or {},
            )
        except Exception as error:
            raise DispatchError("Worker inspection failed") from error


worker_inspector = CeleryWorkerInspector()


WorkerSortKey = Callable[[WorkerRead], str | int | None]

ORDER_FIELDS: dict[str, WorkerSortKey] = {
    "id": lambda worker: worker.id,
    "name": lambda worker: worker.name,
    "status": lambda worker: worker.status,
    "active": lambda worker: worker.active,
    "reserved": lambda worker: worker.reserved,
    "scheduled": lambda worker: worker.scheduled,
    "registered": lambda worker: worker.registered,
    "processed": lambda worker: worker.processed,
    "pid": lambda worker: worker.pid,
    "concurrency": lambda worker: worker.concurrency,
}


class WorkerService:
    def __init__(self, inspector: WorkerInspector | None = None) -> None:
        self.inspector = inspector or worker_inspector

    def list(
        self,
        offset: int,
        limit: int,
        order_by: Sequence[str],
    ) -> tuple[list[WorkerRead], int]:
        order_by = order_by or ["name"]
        self._validate_order_by(order_by)

        workers = self._build_workers(self.inspector.snapshot())
        total = len(workers)

        self._sort(workers, order_by)

        return workers[offset : offset + limit], total

    def _build_workers(self, inspection: WorkerInspection) -> list[WorkerRead]:
        worker_names = sorted(
            {
                *inspection.pings.keys(),
                *inspection.stats.keys(),
                *inspection.active.keys(),
                *inspection.reserved.keys(),
                *inspection.scheduled.keys(),
                *inspection.registered.keys(),
                *inspection.active_queues.keys(),
            }
        )

        return [
            WorkerRead(
                id=name,
                name=name,
                status="online" if name in inspection.pings else "unknown",
                active=len(inspection.active.get(name, [])),
                reserved=len(inspection.reserved.get(name, [])),
                scheduled=len(inspection.scheduled.get(name, [])),
                registered=len(inspection.registered.get(name, [])),
                processed=self._processed_count(inspection.stats.get(name)),
                pid=self._int_stat(inspection.stats.get(name), "pid"),
                concurrency=self._concurrency(inspection.stats.get(name)),
                queues=self._queue_names(inspection.active_queues.get(name, [])),
            )
            for name in worker_names
        ]

    def _sort(self, workers: list[WorkerRead], order_by: Sequence[str]) -> None:
        for order in reversed(order_by or ["name"]):
            descending = order.startswith("-")
            field = order.removeprefix("-").removeprefix("+")
            sort_key = ORDER_FIELDS.get(field)
            assert sort_key is not None

            workers.sort(
                key=lambda worker: self._sortable_value(sort_key(worker)),
                reverse=descending,
            )

    def _validate_order_by(self, order_by: Sequence[str]) -> None:
        for order in order_by:
            field = order.removeprefix("-").removeprefix("+")
            if field not in ORDER_FIELDS:
                raise ValueError(f"Unsupported worker sort field: {field}")

    def _processed_count(self, stats: Any) -> int | None:
        if not isinstance(stats, Mapping):
            return None

        total = stats.get("total")
        if not isinstance(total, Mapping):
            return None

        return sum(value for value in total.values() if isinstance(value, int))

    def _int_stat(self, stats: Any, key: str) -> int | None:
        if not isinstance(stats, Mapping):
            return None

        value = stats.get(key)
        return value if isinstance(value, int) else None

    def _concurrency(self, stats: Any) -> int | None:
        if not isinstance(stats, Mapping):
            return None

        pool = stats.get("pool")
        if not isinstance(pool, Mapping):
            return None

        concurrency = pool.get("max-concurrency")
        return concurrency if isinstance(concurrency, int) else None

    def _queue_names(self, queues: Any) -> list[str]:
        if not isinstance(queues, list):
            return []

        names = []
        for queue in queues:
            if isinstance(queue, Mapping) and isinstance(queue.get("name"), str):
                names.append(queue["name"])

        return names

    def _sortable_value(self, value: str | int | None) -> tuple[bool, str | int]:
        return value is None, "" if value is None else value
