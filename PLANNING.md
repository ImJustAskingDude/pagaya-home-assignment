# Pagaya Queue Management Assignment Plan

## Goal

Build a small full-stack queue management system with:

- React Admin + TypeScript frontend
- Python 3.10+ FastAPI backend
- Celery background worker
- Durable storage and queue state

The assignment values correctness, readability, sensible edge-case behavior, clear design choices, and the ability to explain and evolve the implementation.

## Recommended Scope

Build a pragmatic but defensible MVP:

- Queue CRUD: create, list, rename, delete
- Enqueue tasks into a selected queue
- View queues and tasks, including status
- Task detail with payload, result, failure reason, timestamps, attempts
- Task actions: cancel, retry/requeue, delete
- Background async execution via Celery worker
- README with run instructions, time estimate, design choices, and future improvements
- Focused backend tests around lifecycle and validation

## Recommended Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- Frontend: React Admin, TypeScript 5, Vite
- Database: PostgreSQL
- Queue execution: Celery
- Broker/result infrastructure: Redis for local simplicity
- Local infra: `docker-compose.yml`

Rationale: use established queue infrastructure instead of reimplementing broker behavior. Celery provides mature worker execution, retries, routing, and operational familiarity; Redis keeps local setup simple. PostgreSQL remains the durable application database for user-facing queue/task metadata, auditability, and dashboard queries. React Admin avoids spending assignment time on custom UI polish and gives ready-made CRUD, list, form, filter, and detail views.

## Proposed Repo Layout

```text
backend/
  app/
    api/
    core/
    models/
    schemas/
    services/
    task_handlers/
    celery_app.py
    main.py
  tests/
frontend/
  src/
    dataProvider.ts
    resources/
    App.tsx
docker-compose.yml
README.md
```

## Data Model

Queues:

- `id`
- `name`
- `created_at`
- `updated_at`

Tasks:

- `id`
- `queue_id`
- `celery_task_id`
- `type`
- `payload`
- `status`
- `result`
- `error`
- `attempts`
- `max_attempts`
- `created_at`
- `started_at`
- `finished_at`
- `cancel_requested_at`

Optional if time permits:

- `task_events` table for lifecycle audit history

## Task Statuses

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

## Task Types

Implement a small clear set:

- `wait`: sleep for `seconds`, then succeed
- `echo`: return/store a message string
- `compute_hash`: compute SHA256 for a provided string
- `random_fail`: succeed/fail based on a probability
- `count_primes`: count primes up to `n`

Optional if time permits:

- `json_transform`
- `batch/fanout`

## Worker Design

Use Celery for actual job dispatch and execution:

- FastAPI validates the request and creates a `tasks` metadata row in PostgreSQL.
- FastAPI records the selected logical queue on the task metadata row and enqueues the execution on Celery.
- Store the returned `celery_task_id` on the metadata row.
- Celery worker executes the task handler and updates PostgreSQL with `running`, `succeeded`, `failed`, or `cancelled`.
- Redis is the local broker/result infrastructure.

This delegates delivery, worker coordination, and retry mechanics to established infrastructure while keeping durable task history queryable for the UI.

## Cancellation Behavior

- Queued task: revoke the Celery task if possible, mark the metadata row as `cancelled`, and make the worker no-op if the message is still delivered.
- Running task: cooperative cancellation
  - API marks `cancel_requested_at`
  - Worker checks before and after execution
  - `wait` should check during sleep
  - `count_primes` can check between chunks

This is realistic and easy to explain in review.

## Retry Behavior

- Use Celery retry support for task-level retry execution.
- Persist attempt counts and terminal errors in PostgreSQL for the dashboard.
- Manual retry from the API should enqueue a new Celery execution for an existing failed/cancelled task or create a replacement task row, depending on which is simpler to explain cleanly.
- Keep `max_attempts` simple and explicit.

## Frontend Shape

Build a practical React Admin interface:

- `queues` resource with list/create/edit/delete.
- `tasks` resource with list/show/delete.
- Task list should show status, type, queue, attempts, created/started/finished timestamps.
- Task show view should display payload, result, error, and Celery task id.
- Custom task create form should provide task type selector and typed payload inputs.
- Custom row/show actions: cancel and retry.
- Poll/refetch task data every 1-2 seconds for status updates if straightforward.

Avoid custom visual design work beyond what is needed for clarity. React Admin's default Material UI layout is acceptable and appropriate for the assignment.

## Implementation Order

1. Scaffold repo, Docker Compose, backend app, frontend app.
2. Add PostgreSQL, Redis, FastAPI, Celery, and React Admin configuration.
3. Define DB models and migrations.
4. Implement queue/task metadata services and FastAPI routes.
5. Implement Celery app, task handlers, and worker status updates.
6. Add focused backend tests.
7. Build React Admin resources, data provider, and custom task actions.
8. Write README with tradeoffs and next steps.

## Design Talking Points

- Celery/Redis handles job dispatch and worker execution instead of custom queue mechanics.
- PostgreSQL is the durable source of truth for application metadata and task history.
- Worker is stateless and horizontally scalable through Celery.
- Task state transitions are explicit and easy to reason about.
- Cancellation is cooperative for running tasks, immediate for queued tasks.
- Retry behavior uses Celery primitives while persisting user-facing attempt/error state.
- React Admin keeps UI effort focused on operational workflows rather than custom styling.
- Polling is sufficient for the assignment; WebSocket/SSE can be a future improvement.

## Things To Avoid

- Avoid custom queue claiming/locking logic; use Celery for queue execution.
- Avoid in-process FastAPI background tasks; the assignment asks for API + worker.
- Avoid overbuilding orchestration, auth, permissions, or complex scheduling.
- Avoid custom UI polish; React Admin defaults are enough.

## README Must Include

- How to run locally
- How long the assignment took
- Design choices and tradeoffs
- What would be improved with more time

## Future Improvements

- Richer retry policies with backoff/jitter
- Dead-letter queue
- Task event history
- WebSocket/SSE live updates
- Worker heartbeats and stuck-task recovery
- Queue pausing/resuming
- Priority queues
- Pagination and filtering at larger scale
- Authentication/authorization
