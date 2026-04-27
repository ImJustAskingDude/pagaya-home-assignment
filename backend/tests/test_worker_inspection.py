from fastapi.testclient import TestClient
import pytest

from app.services.workers import WorkerInspection
import app.services.workers as worker_service_module


class FakeWorkerInspector:
    def snapshot(self) -> WorkerInspection:
        return WorkerInspection(
            pings={"worker-b@example": {"ok": "pong"}, "worker-a@example": {"ok": "pong"}},
            stats={
                "worker-b@example": {
                    "pid": 202,
                    "pool": {"max-concurrency": 4},
                    "total": {"tasks.execute": 7},
                },
                "worker-a@example": {
                    "pid": 101,
                    "pool": {"max-concurrency": 2},
                    "total": {"tasks.execute": 3},
                },
            },
            active={"worker-b@example": [{}, {}], "worker-a@example": [{}]},
            reserved={"worker-b@example": [{}], "worker-a@example": []},
            scheduled={"worker-b@example": [], "worker-a@example": [{}, {}]},
            registered={"worker-b@example": ["tasks.execute"], "worker-a@example": ["tasks.execute"]},
            active_queues={
                "worker-b@example": [{"name": "celery"}],
                "worker-a@example": [{"name": "celery"}],
            },
        )


def test_workers_list_reads_celery_inspection_snapshot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_service_module, "worker_inspector", FakeWorkerInspector())

    response = client.get("/api/workers", params={"order_by": "-active", "limit": 1})

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "2"
    assert response.json()["total"] == 2
    assert response.json()["items"] == [
        {
            "id": "worker-b@example",
            "name": "worker-b@example",
            "status": "online",
            "active": 2,
            "reserved": 1,
            "scheduled": 0,
            "registered": 1,
            "processed": 7,
            "pid": 202,
            "concurrency": 4,
            "queues": ["celery"],
        }
    ]


def test_workers_list_rejects_unknown_sort_field(client: TestClient) -> None:
    response = client.get("/api/workers", params={"order_by": "not_a_field"})

    assert response.status_code == 422
