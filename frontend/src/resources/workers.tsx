import { Datagrid, FunctionField, List, NumberField, TextField } from "react-admin";

type WorkerRecord = {
  id: string;
  queues: string[];
};

export function WorkerList() {
  return (
    <List
      actions={false}
      pagination={false}
      perPage={100}
      queryOptions={{ refetchInterval: 5000 }}
      sort={{ field: "name", order: "ASC" }}
    >
      <Datagrid rowClick={false} bulkActionButtons={false}>
        <TextField source="name" />
        <TextField source="status" />
        <NumberField source="active" />
        <NumberField source="reserved" />
        <NumberField source="scheduled" />
        <NumberField source="registered" />
        <NumberField source="processed" />
        <NumberField source="pid" />
        <NumberField source="concurrency" />
        <FunctionField<WorkerRecord>
          label="Queues"
          render={(record) => (record?.queues.length ? record.queues.join(", ") : "-")}
        />
      </Datagrid>
    </List>
  );
}
