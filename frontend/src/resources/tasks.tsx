import CancelIcon from "@mui/icons-material/Cancel";
import ReplayIcon from "@mui/icons-material/Replay";
import { useEffect, type MouseEvent } from "react";
import {
  Button,
  Create,
  Datagrid,
  DateField,
  DeleteButton,
  FormDataConsumer,
  Labeled,
  List,
  NumberInput,
  ReferenceField,
  ReferenceInput,
  SelectInput,
  Show,
  ShowButton,
  SimpleForm,
  SimpleShowLayout,
  TextField,
  TextInput,
  TopToolbar,
  useNotify,
  useRecordContext,
  useRefresh,
} from "react-admin";
import { useFormContext, useWatch } from "react-hook-form";

import { apiUrl } from "../config";
import { JsonField } from "../components/JsonField";
import { useNotificationCenter } from "../components/NotificationCenter";

const taskTypeChoices = [
  { id: "echo", name: "echo" },
  { id: "wait", name: "wait" },
  { id: "compute_hash", name: "compute_hash" },
  { id: "random_fail", name: "random_fail" },
  { id: "count_primes", name: "count_primes" },
  { id: "json_transform", name: "json_transform" },
  { id: "batch_fanout", name: "batch_fanout" },
];

const statusChoices = [
  { id: "queued", name: "queued" },
  { id: "running", name: "running" },
  { id: "succeeded", name: "succeeded" },
  { id: "failed", name: "failed" },
  { id: "cancelled", name: "cancelled" },
];

type TaskRecord = {
  id: number;
  status: string;
};

type TaskCreateFormData = {
  scenario?: string;
  type?: string;
  max_attempts?: number;
  payload?: Record<string, unknown>;
};

type TaskScenario = {
  id: string;
  name: string;
  type: string;
  max_attempts: number;
  payload: Record<string, unknown>;
};

const taskScenarios: TaskScenario[] = [
  {
    id: "json_transform_select_rename",
    name: "JSON transform: select + rename",
    type: "json_transform",
    max_attempts: 1,
    payload: {
      input: JSON.stringify({ id: 42, name: "Ada", role: "engineer", hidden: true }, null, 2),
      select_keys: JSON.stringify(["id", "name", "role"], null, 2),
      rename_keys: JSON.stringify({ id: "user_id", role: "title" }, null, 2),
    },
  },
  {
    id: "batch_fanout_three_echoes",
    name: "Batch fanout: 3 echo children",
    type: "batch_fanout",
    max_attempts: 1,
    payload: {
      child_count: 3,
      message_prefix: "fanout child",
      child_max_attempts: 1,
    },
  },
];

const taskScenarioChoices = taskScenarios.map(({ id, name }) => ({ id, name }));

const parseJsonValue = (value: unknown, fallback: unknown) => {
  if (typeof value !== "string") {
    return value ?? fallback;
  }

  if (value.trim() === "") {
    return fallback;
  }

  return JSON.parse(value);
};

const parseJsonObject = (value: unknown, fallback: Record<string, unknown>) => {
  const parsed = parseJsonValue(value, fallback);

  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Expected JSON object");
  }

  return parsed as Record<string, unknown>;
};

const parseJsonArray = (value: unknown) => {
  const parsed = parseJsonValue(value, null);

  if (parsed === null) {
    return null;
  }

  if (!Array.isArray(parsed)) {
    throw new Error("Expected JSON array");
  }

  return parsed;
};

const transformTaskCreate = (formData: TaskCreateFormData) => {
  const { scenario: _scenario, ...data } = formData;

  if (data.type !== "json_transform") {
    return data;
  }

  const payload = data.payload ?? {};
  return {
    ...data,
    payload: {
      input: parseJsonObject(payload.input, {}),
      select_keys: parseJsonArray(payload.select_keys),
      rename_keys: parseJsonObject(payload.rename_keys, {}),
    },
  };
};

function TaskScenarioInput() {
  const { setValue } = useFormContext();
  const scenarioId = useWatch({ name: "scenario" });

  useEffect(() => {
    if (typeof scenarioId !== "string") {
      return;
    }

    const scenario = taskScenarios.find((item) => item.id === scenarioId);
    if (!scenario) {
      return;
    }

    setValue("type", scenario.type, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue("max_attempts", scenario.max_attempts, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue("payload", scenario.payload, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
  }, [scenarioId, setValue]);

  return <SelectInput source="scenario" label="Scenario" choices={taskScenarioChoices} emptyText="Custom" />;
}

function TaskCommandButton({ command }: { command: "cancel" | "retry" }) {
  const record = useRecordContext<TaskRecord>();
  const { addNotification } = useNotificationCenter();
  const notify = useNotify();
  const refresh = useRefresh();
  const isCancel = command === "cancel";
  const enabled = record
    ? isCancel
      ? ["queued", "running"].includes(record.status)
      : !["queued", "running"].includes(record.status)
    : false;

  const handleClick = async (event: MouseEvent) => {
    event.stopPropagation();

    if (!record) {
      return;
    }

    const response = await fetch(`${apiUrl}/tasks/${record.id}/${command}`, { method: "POST" });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Request failed" }));
      notify(body.detail ?? "Request failed", { type: "error" });
      return;
    }

    addNotification({ message: `Task ${record.id} ${command} requested` });
    refresh();
  };

  return (
    <Button label={isCancel ? "Cancel" : "Retry"} onClick={handleClick} disabled={!enabled}>
      {isCancel ? <CancelIcon /> : <ReplayIcon />}
    </Button>
  );
}

function TaskActions() {
  return (
    <TopToolbar>
      <TaskCommandButton command="cancel" />
      <TaskCommandButton command="retry" />
      <DeleteButton mutationMode="pessimistic" />
    </TopToolbar>
  );
}

function PayloadInputs() {
  return (
    <FormDataConsumer>
      {({ formData }) => {
        switch (formData?.type) {
          case "wait":
            return <NumberInput source="payload.seconds" label="Seconds" min={0.1} max={60} required />;
          case "compute_hash":
            return <TextInput source="payload.value" label="Value" required fullWidth multiline />;
          case "random_fail":
            return <NumberInput source="payload.probability" label="Failure probability" min={0} max={1} required />;
          case "count_primes":
            return <NumberInput source="payload.n" label="Count primes up to" min={0} max={200000} required />;
          case "json_transform":
            return (
              <>
                <TextInput source="payload.input" label="Input JSON" required fullWidth multiline />
                <TextInput source="payload.select_keys" label="Select keys" fullWidth multiline />
                <TextInput source="payload.rename_keys" label="Rename map" fullWidth multiline />
              </>
            );
          case "batch_fanout":
            return (
              <>
                <NumberInput source="payload.child_count" label="Child count" min={1} max={100} required />
                <TextInput source="payload.message_prefix" label="Message prefix" required fullWidth />
                <NumberInput source="payload.child_max_attempts" label="Child max attempts" min={1} max={10} required />
              </>
            );
          case "echo":
          default:
            return <TextInput source="payload.message" label="Message" required fullWidth multiline />;
        }
      }}
    </FormDataConsumer>
  );
}

export function TaskList() {
  return (
    <List
      sort={{ field: "created_at", order: "DESC" }}
      queryOptions={{ refetchInterval: 2000 }}
      filters={[
        <ReferenceInput key="queue_id" source="queue_id" reference="queues" alwaysOn />,
        <SelectInput key="status" source="status" choices={statusChoices} alwaysOn />,
        <SelectInput key="type" source="type" choices={taskTypeChoices} />,
      ]}
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="id" />
        <ReferenceField source="queue_id" reference="queues" link="show">
          <TextField source="name" />
        </ReferenceField>
        <TextField source="type" />
        <TextField source="status" />
        <TextField source="attempts" />
        <TextField source="max_attempts" />
        <DateField source="created_at" showTime />
        <DateField source="started_at" showTime />
        <DateField source="finished_at" showTime />
        <ShowButton />
        <TaskCommandButton command="cancel" />
        <TaskCommandButton command="retry" />
        <DeleteButton mutationMode="pessimistic" />
      </Datagrid>
    </List>
  );
}

export function TaskResultList() {
  return (
    <List
      disableSyncWithLocation
      sort={{ field: "created_at", order: "DESC" }}
      storeKey="task-results.resultListParams"
      queryOptions={{ refetchInterval: 2000 }}
      filters={[
        <ReferenceInput key="queue_id" source="queue_id" reference="queues" alwaysOn />,
        <SelectInput key="status" source="status" choices={statusChoices} alwaysOn />,
        <SelectInput key="type" source="type" choices={taskTypeChoices} />,
      ]}
    >
      <Datagrid rowClick={false} bulkActionButtons={false}>
        <TextField source="id" />
        <TextField source="task_id" />
        <ReferenceField source="queue_id" reference="queues" link="show">
          <TextField source="name" />
        </ReferenceField>
        <TextField source="type" />
        <TextField source="status" />
        <DateField source="created_at" showTime />
        <Labeled label="Result">
          <JsonField source="result" />
        </Labeled>
        <TextField source="error" />
      </Datagrid>
    </List>
  );
}

export function TaskCreate() {
  return (
    <Create redirect="show" transform={transformTaskCreate}>
      <SimpleForm
        defaultValues={{
          type: "echo",
          scenario: "",
          max_attempts: 1,
          payload: {
            message: "",
            input: "{}",
            select_keys: "",
            rename_keys: "{}",
            child_count: 3,
            message_prefix: "child",
            child_max_attempts: 1,
          },
        }}
      >
        <ReferenceInput source="queue_id" reference="queues">
          <SelectInput optionText="name" required />
        </ReferenceInput>
        <TaskScenarioInput />
        <SelectInput source="type" choices={taskTypeChoices} required />
        <PayloadInputs />
        <NumberInput source="max_attempts" min={1} max={10} required />
      </SimpleForm>
    </Create>
  );
}

export function TaskShow() {
  return (
    <Show actions={<TaskActions />} queryOptions={{ refetchInterval: 2000 }}>
      <SimpleShowLayout>
        <TextField source="id" />
        <ReferenceField source="queue_id" reference="queues" link="show">
          <TextField source="name" />
        </ReferenceField>
        <TextField source="celery_task_id" />
        <TextField source="type" />
        <TextField source="status" />
        <TextField source="attempts" />
        <TextField source="max_attempts" />
        <DateField source="created_at" showTime />
        <DateField source="started_at" showTime />
        <DateField source="finished_at" showTime />
        <DateField source="cancel_requested_at" showTime />
        <Labeled label="Payload">
          <JsonField source="payload" />
        </Labeled>
        <Labeled label="Result">
          <JsonField source="result" />
        </Labeled>
        <TextField source="error" />
      </SimpleShowLayout>
    </Show>
  );
}
