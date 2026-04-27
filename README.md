# Pagaya Queue Manager

Small full-stack queue management system built with FastAPI, PostgreSQL, Celery, Redis, and React Admin.

## What It Does

- Create, list, edit, and delete logical queues.
- Enqueue tasks into a selected queue.
- Execute tasks asynchronously through Celery workers.
- Store durable task metadata, payloads, results, errors, attempts, and timestamps in PostgreSQL.
- Preserve task result history across retries.
- Cancel queued/running tasks cooperatively.
- Retry any finished task.
- Inspect queues, tasks, task results, and Celery workers through a React Admin UI.
- Use built-in task creation scenarios to quickly exercise representative workflows.

## How This Was Built

This project was developed through an iterative review loop with Codex. The initial implementation was followed by focused review comments about API typing, Pydantic validation style, transaction boundaries, repository/service separation, task result history, UI workflow polish, and e2e coverage. Each meaningful change was made in small commits so the reasoning and code evolution are reviewable.

The full project-scoped conversation transcript is included in [`CONVERSATION_TRANSCRIPT.md`](CONVERSATION_TRANSCRIPT.md). It was generated from local Codex session logs using [`export_codex_transcripts.py`](export_codex_transcripts.py), ordered by session timestamp, and filtered to this repository. Reviewers can use it to see the decisions, tradeoffs, and implementation steps that led to the final code.

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
4. Terminal executions are copied into `task_results`, so retries keep historical results.
5. React Admin polls task, task result, and worker data to show current status.

The backend is split into API routers, Pydantic schemas, SQLAlchemy models,
repositories, services, and task handlers. Services own application behavior and
use a small `UnitOfWork` wrapper for transaction boundaries. Models expose small
domain methods for state changes such as queue rename, task retry reset, running,
success, failure, and cancellation.

## Task Types

- `echo`: returns a message.
- `wait`: sleeps for a bounded number of seconds.
- `compute_hash`: computes SHA256 for a string.
- `random_fail`: fails based on a probability.
- `count_primes`: counts prime numbers up to `n`.
- `json_transform`: selects and optionally renames keys from an input JSON object.
- `batch_fanout`: creates N child `echo` tasks on the same logical queue.

The Task create form includes a `Scenario` selector with ready-to-run examples
for `json_transform` and `batch_fanout`, so the demo flows can be exercised
without hand-writing payloads.

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
- `GET /api/task-results`
- `GET /api/task-results/{id}`
- `GET /api/workers`

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
- Manual retry resets any finished task row and enqueues a new Celery execution.
- Task results are stored separately from task state, so repeated retries preserve each execution result.
- `batch_fanout` intentionally creates simple child `echo` tasks instead of introducing a full parent/child execution model.
- Celery worker inspection is runtime state, so it is exposed through Celery inspect instead of persisted as a database resource.
- ORM models use SQLAlchemy native dataclass mapping with keyword-only constructors,
  keeping application-set fields explicit while database- and worker-owned fields
  stay managed internally.

## Tradeoffs And Future Work

- Named Celery queues per logical queue would require consumer management for dynamically created queues.
- Celery task dispatch and database writes are not wrapped in a transactional outbox; that would be the next reliability improvement.
- Add richer retry backoff/jitter policies and dead-letter handling.
- Add worker heartbeat and stuck-task recovery.
- Add richer task event history for auditability.
- Add pagination/filter polish and authentication for production use.
- Replace polling with SSE/WebSocket updates if live status becomes important.

## Tests

There are focused backend tests for payload validation, ORM constructor ergonomics,
queue/task API lifecycle behavior, task result preservation, worker inspection,
and worker model import wiring:

```bash
cd backend
pytest
```

There are also Playwright e2e tests that exercise the real API, database,
Redis broker, and Celery worker through queue/task workflows:

```bash
docker compose up --build
cd frontend
npm run test:e2e
```

The tests expect the API at `http://localhost:8000/api` by default. Override it
with `E2E_API_URL` when using a custom port:

```bash
E2E_API_URL=http://localhost:18000/api npm run test:e2e
```

The concurrent submission test creates 20 tasks by default. Override that with
`E2E_STRESS_TASKS`.

## Time Spent

Approximately 4 hours for the original assignment implementation scope, followed
by additional review-driven polish, refactoring, UI improvements, and e2e
coverage.
