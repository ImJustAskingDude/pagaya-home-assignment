import CancelIcon from "@mui/icons-material/Cancel";
import ReplayIcon from "@mui/icons-material/Replay";
import type { MouseEvent } from "react";
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

import { apiUrl } from "../config";
import { JsonField } from "../components/JsonField";
import { useNotificationCenter } from "../components/NotificationCenter";

const taskTypeChoices = [
  { id: "echo", name: "echo" },
  { id: "wait", name: "wait" },
  { id: "compute_hash", name: "compute_hash" },
  { id: "random_fail", name: "random_fail" },
  { id: "count_primes", name: "count_primes" },
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
    <Create redirect="show">
      <SimpleForm defaultValues={{ type: "echo", max_attempts: 1, payload: { message: "" } }}>
        <ReferenceInput source="queue_id" reference="queues">
          <SelectInput optionText="name" required />
        </ReferenceInput>
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
