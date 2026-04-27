import { createHash } from "node:crypto";
import { expect, test, type APIRequestContext, type APIResponse } from "@playwright/test";

type QueueRecord = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
};

type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
type TaskType = "echo" | "wait" | "compute_hash" | "random_fail" | "count_primes";

type TaskRecord = {
  id: number;
  queue_id: number;
  celery_task_id: string | null;
  type: TaskType;
  payload: Record<string, unknown>;
  status: TaskStatus;
  result: Record<string, unknown> | null;
  error: string | null;
  attempts: number;
  max_attempts: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested_at: string | null;
};

type ListResponse<T> = {
  items: T[];
  total: number;
};

type TaskCreatePayload = {
  queue_id: number;
  type: TaskType;
  payload: Record<string, unknown>;
  max_attempts?: number;
};

const activeStatuses = new Set<TaskStatus>(["queued", "running"]);
const runId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const response = await request.get("queues?limit=1");
  expect(
    response.ok(),
    `E2E API is not reachable at ${response.url()}. Start the app stack before running Playwright tests.`,
  ).toBe(true);
});

test("manages queues and preserves user-provided names", async ({ request }) => {
  let queueId: number | undefined;

  try {
    const name = ` e2e queue ${runId} `;
    const queue = await createQueue(request, name);
    queueId = queue.id;

    expect(queue.name).toBe(name);

    const filtered = await getList<QueueRecord>(request, "queues", {
      name: `e2e queue ${runId}`,
      order_by: "id",
    });
    expect(filtered.items.map((item) => item.id)).toContain(queue.id);

    const renamed = ` e2e renamed queue ${runId} `;
    const updated = await jsonOk<QueueRecord>(
      await request.put(`queues/${queue.id}`, { data: { name: renamed } }),
    );
    expect(updated.name).toBe(renamed);

    const duplicate = await request.post("queues", { data: { name: renamed } });
    expect(duplicate.status()).toBe(409);

    await jsonOk<QueueRecord>(await request.delete(`queues/${queue.id}`));
    queueId = undefined;
  } finally {
    if (queueId !== undefined) {
      await deleteQueueIfExists(request, queueId);
    }
  }
});

test("executes each supported task type end to end", async ({ request }) => {
  const taskIds: number[] = [];
  let queueId: number | undefined;

  try {
    const queue = await createQueue(request, `e2e task types ${runId}`);
    queueId = queue.id;
    const hashValue = `hash-${runId}`;

    const createdTasks = await Promise.all([
      createTask(request, {
        queue_id: queue.id,
        type: "echo",
        payload: { message: `hello-${runId}` },
      }),
      createTask(request, {
        queue_id: queue.id,
        type: "wait",
        payload: { seconds: 0.1 },
      }),
      createTask(request, {
        queue_id: queue.id,
        type: "compute_hash",
        payload: { value: hashValue },
      }),
      createTask(request, {
        queue_id: queue.id,
        type: "random_fail",
        payload: { probability: 0 },
      }),
      createTask(request, {
        queue_id: queue.id,
        type: "count_primes",
        payload: { n: 20 },
      }),
    ]);
    taskIds.push(...createdTasks.map((task) => task.id));

    const finishedTasks = await Promise.all(
      createdTasks.map((task) =>
        waitForTask(
          request,
          task.id,
          (current) => current.status === "succeeded",
          `task ${task.id} to succeed`,
        ),
      ),
    );

    const byType = new Map(finishedTasks.map((task) => [task.type, task]));
    expect(byType.get("echo")?.result).toEqual({ message: `hello-${runId}` });
    expect(byType.get("wait")?.result?.waited_seconds).toBeCloseTo(0.1);
    expect(byType.get("compute_hash")?.result).toEqual({
      algorithm: "sha256",
      digest: createHash("sha256").update(hashValue).digest("hex"),
    });
    expect(byType.get("random_fail")?.result).toEqual({ succeeded: true, probability: 0 });
    expect(byType.get("count_primes")?.result).toEqual({ n: 20, prime_count: 8 });

    const listed = await getList<TaskRecord>(request, "tasks", {
      id__in: taskIds.join(","),
      limit: "100",
      order_by: "id",
    });
    expect(listed.total).toBe(taskIds.length);
    expect(listed.items.map((task) => task.id).sort((a, b) => a - b)).toEqual(
      [...taskIds].sort((a, b) => a - b),
    );
  } finally {
    await cleanupTasks(request, taskIds);
    if (queueId !== undefined) {
      await deleteQueueIfExists(request, queueId);
    }
  }
});

test("blocks active deletion, cancels active tasks, and retries finished tasks", async ({ request }) => {
  const taskIds: number[] = [];
  let queueId: number | undefined;

  try {
    const queue = await createQueue(request, `e2e commands ${runId}`);
    queueId = queue.id;

    const cancellable = await createTask(request, {
      queue_id: queue.id,
      type: "wait",
      payload: { seconds: 5 },
    });
    taskIds.push(cancellable.id);

    const activeDelete = await request.delete(`tasks/${cancellable.id}`);
    expect(activeDelete.status()).toBe(409);

    await jsonOk<TaskRecord>(await request.post(`tasks/${cancellable.id}/cancel`));
    const cancelled = await waitForTask(
      request,
      cancellable.id,
      (current) => current.status === "cancelled",
      `task ${cancellable.id} to cancel`,
    );
    expect(cancelled.cancel_requested_at).not.toBeNull();

    await jsonOk<TaskRecord>(await request.delete(`tasks/${cancellable.id}`));
    taskIds.splice(taskIds.indexOf(cancellable.id), 1);

    const failing = await createTask(request, {
      queue_id: queue.id,
      type: "random_fail",
      payload: { probability: 1 },
      max_attempts: 1,
    });
    taskIds.push(failing.id);

    const failed = await waitForTask(
      request,
      failing.id,
      (current) => current.status === "failed",
      `task ${failing.id} to fail`,
    );
    expect(failed.error).toContain("Random failure at probability 1");

    await jsonOk<TaskRecord>(await request.post(`tasks/${failing.id}/retry`));
    const retried = await waitForTask(
      request,
      failing.id,
      (current) => current.status === "failed" && current.celery_task_id !== failed.celery_task_id,
      `task ${failing.id} retry to fail again`,
    );
    expect(retried.attempts).toBe(1);
    expect(retried.error).toContain("Random failure at probability 1");

    const successful = await createTask(request, {
      queue_id: queue.id,
      type: "echo",
      payload: { message: `retry-success-${runId}` },
    });
    taskIds.push(successful.id);

    const succeeded = await waitForTask(
      request,
      successful.id,
      (current) => current.status === "succeeded",
      `task ${successful.id} to succeed`,
    );
    expect(succeeded.result).toEqual({ message: `retry-success-${runId}` });

    await jsonOk<TaskRecord>(await request.post(`tasks/${successful.id}/retry`));
    const retriedSuccess = await waitForTask(
      request,
      successful.id,
      (current) => current.status === "succeeded" && current.celery_task_id !== succeeded.celery_task_id,
      `task ${successful.id} retry to succeed again`,
    );
    expect(retriedSuccess.result).toEqual({ message: `retry-success-${runId}` });
  } finally {
    await cleanupTasks(request, taskIds);
    if (queueId !== undefined) {
      await deleteQueueIfExists(request, queueId);
    }
  }
});

test("handles concurrent task submissions under load", async ({ request }) => {
  const stressTaskCount = Number(process.env.E2E_STRESS_TASKS ?? "20");
  const taskIds: number[] = [];
  let queueId: number | undefined;

  try {
    const queue = await createQueue(request, `e2e stress ${runId}`);
    queueId = queue.id;

    const createdTasks = await Promise.all(
      Array.from({ length: stressTaskCount }, (_, index) =>
        createTask(request, {
          queue_id: queue.id,
          type: "echo",
          payload: { message: `stress-${runId}-${index}` },
        }),
      ),
    );
    taskIds.push(...createdTasks.map((task) => task.id));

    const finishedTasks = await Promise.all(
      createdTasks.map((task) =>
        waitForTask(
          request,
          task.id,
          (current) => current.status === "succeeded",
          `stress task ${task.id} to succeed`,
          45_000,
        ),
      ),
    );

    expect(finishedTasks).toHaveLength(stressTaskCount);
    for (const task of finishedTasks) {
      expect(task.result).toEqual({ message: task.payload.message });
    }
  } finally {
    await cleanupTasks(request, taskIds);
    if (queueId !== undefined) {
      await deleteQueueIfExists(request, queueId);
    }
  }
});

async function createQueue(request: APIRequestContext, name: string): Promise<QueueRecord> {
  return jsonOk<QueueRecord>(await request.post("queues", { data: { name } }), 201);
}

async function createTask(request: APIRequestContext, payload: TaskCreatePayload): Promise<TaskRecord> {
  return jsonOk<TaskRecord>(await request.post("tasks", { data: payload }), 201);
}

async function getList<T>(
  request: APIRequestContext,
  path: string,
  params: Record<string, string>,
): Promise<ListResponse<T>> {
  const response = await request.get(`${path}?${new URLSearchParams(params).toString()}`);
  return jsonOk<ListResponse<T>>(response);
}

async function jsonOk<T>(response: APIResponse, expectedStatus?: number): Promise<T> {
  const body = await response.text();
  if (expectedStatus === undefined) {
    expect(response.ok(), `${response.url()} failed with ${response.status()}: ${body}`).toBe(true);
  } else {
    expect(response.status(), `${response.url()} returned: ${body}`).toBe(expectedStatus);
  }
  return JSON.parse(body) as T;
}

async function waitForTask(
  request: APIRequestContext,
  taskId: number,
  predicate: (task: TaskRecord) => boolean,
  description: string,
  timeoutMs = 30_000,
): Promise<TaskRecord> {
  const deadline = Date.now() + timeoutMs;
  let lastTask: TaskRecord | undefined;

  while (Date.now() < deadline) {
    const response = await request.get(`tasks/${taskId}`);
    lastTask = await jsonOk<TaskRecord>(response);
    if (predicate(lastTask)) {
      return lastTask;
    }
    await delay(250);
  }

  throw new Error(`Timed out waiting for ${description}. Last task state: ${JSON.stringify(lastTask)}`);
}

async function cleanupTasks(request: APIRequestContext, taskIds: number[]): Promise<void> {
  for (const taskId of [...taskIds].reverse()) {
    await deleteTaskIfExists(request, taskId);
  }
}

async function deleteTaskIfExists(request: APIRequestContext, taskId: number): Promise<void> {
  const response = await request.get(`tasks/${taskId}`);
  if (response.status() === 404) {
    return;
  }

  let task = await jsonOk<TaskRecord>(response);
  if (activeStatuses.has(task.status)) {
    await request.post(`tasks/${taskId}/cancel`);
    task = await waitForTask(
      request,
      taskId,
      (current) => !activeStatuses.has(current.status),
      `task ${taskId} to leave active status during cleanup`,
    );
  }

  const deleteResponse = await request.delete(`tasks/${task.id}`);
  if (deleteResponse.status() !== 404) {
    await jsonOk<TaskRecord>(deleteResponse);
  }
}

async function deleteQueueIfExists(request: APIRequestContext, queueId: number): Promise<void> {
  const response = await request.delete(`queues/${queueId}`);
  if (response.status() !== 404) {
    await jsonOk<QueueRecord>(response);
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
