# Pagaya Queue Manager

Small full-stack queue management system built with FastAPI, PostgreSQL, Celery, Redis, and React Admin.

## What It Does

- Create, list, edit, and delete logical queues.
- Enqueue tasks into a selected queue.
- Execute tasks asynchronously through Celery workers.
- Store durable task metadata, payloads, results, errors, attempts, and timestamps in PostgreSQL.
- Cancel queued/running tasks cooperatively.
- Retry failed or cancelled tasks.
- Inspect queues and tasks through a React Admin UI.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- Queue execution: Celery
- Broker/result backend: Redis
- Database: PostgreSQL
- Frontend: React Admin, Vite, TypeScript, Material UI
- Local infra: Docker Compose

## Run Locally

The project is containerized. From the repo root:

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The frontend container runs as `${UID:-1000}:${GID:-1000}` so files created
through the bind mount stay owned by the host user. If your local UID/GID are
not `1000`, start Compose with `UID=$(id -u) GID=$(id -g) docker compose up --build`.

If those host ports are already in use, override them when starting Compose:

```bash
API_PORT=18000 FRONTEND_PORT=15173 docker compose up --build
```

Then open the matching frontend and API URLs for those ports. PostgreSQL and
Redis are used only inside the Compose network and are not published to the
host by default.

To stop:

```bash
docker compose down
```

To remove the database volume:

```bash
docker compose down -v
```

## Architecture

FastAPI owns validation and application-level commands. PostgreSQL stores queues and task metadata. Celery owns asynchronous execution, worker coordination, retry execution, and broker interaction through Redis.

Queues are modeled as product-level logical queues. The MVP intentionally uses one Celery physical queue to keep CRUD-created queues simple and robust in local development. A production extension could route specific logical queues to named Celery queues and manage worker consumers per queue.

Task flow:

1. API validates the request and inserts a `tasks` row with `queued` status.
2. API enqueues a Celery job and stores the Celery task id.
3. Worker marks the row `running`, executes the selected handler, and persists `succeeded`, `failed`, or `cancelled`.
4. React Admin polls task data to show current status.

## Task Types

- `echo`: returns a message.
- `wait`: sleeps for a bounded number of seconds.
- `compute_hash`: computes SHA256 for a string.
- `random_fail`: fails based on a probability.
- `count_primes`: counts prime numbers up to `n`.

## API Shape

Main resources:

- `GET /api/queues`
- `POST /api/queues`
- `GET /api/queues/{id}`
- `PUT /api/queues/{id}`
- `DELETE /api/queues/{id}`
- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks/{id}/cancel`
- `POST /api/tasks/{id}/retry`
- `DELETE /api/tasks/{id}`

List endpoints accept `offset`, `limit`, resource-specific filter query parameters, and `order_by`.
Filtering uses `fastapi-filter` syntax, for example
`GET /api/tasks?status=queued&type=echo&order_by=-created_at` or
`GET /api/tasks?id__in=1,2,3`. This matches the custom React Admin data provider.

## Design Choices

- Celery/Redis is used instead of custom PostgreSQL row-lock queue claiming to avoid reinventing broker mechanics.
- PostgreSQL remains the durable source of truth for UI-visible state and task history.
- React Admin is used to avoid spending time on custom UI for an operational CRUD dashboard.
- Cancellation is cooperative for running tasks. The API records cancellation intent; handlers check during longer work.
- Queue deletion is blocked while queued or running tasks exist, avoiding surprising active-task deletion.
- Active task deletion is blocked; cancel first, then delete after the task reaches a terminal state.
- Manual retry resets a failed/cancelled task row and enqueues a new Celery execution.
- ORM models use SQLAlchemy native dataclass mapping with keyword-only constructors,
  keeping application-set fields explicit while database- and worker-owned fields
  stay managed internally.

## Tradeoffs And Future Work

- Named Celery queues per logical queue would require consumer management for dynamically created queues.
- Celery task dispatch and database writes are not wrapped in a transactional outbox; that would be the next reliability improvement.
- Add richer retry backoff/jitter policies and dead-letter handling.
- Add worker heartbeat and stuck-task recovery.
- Add task event history for auditability.
- Add pagination/filter polish and authentication for production use.
- Replace polling with SSE/WebSocket updates if live status becomes important.

## Tests

There are focused backend tests for payload validation, ORM constructor ergonomics,
queue/task API lifecycle behavior, and worker model import wiring:

```bash
cd backend
pytest
```

## Time Spent

Approximately 4 hours for the intended assignment implementation scope.
