import {
  Create,
  Datagrid,
  DateField,
  DeleteButton,
  Edit,
  EditButton,
  List,
  ReferenceManyField,
  Show,
  ShowButton,
  SimpleForm,
  SimpleShowLayout,
  TextField,
  TextInput,
} from "react-admin";

export function QueueList() {
  return (
    <List sort={{ field: "id", order: "ASC" }}>
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="id" />
        <TextField source="name" />
        <DateField source="created_at" showTime />
        <DateField source="updated_at" showTime />
        <ShowButton />
        <EditButton />
        <DeleteButton />
      </Datagrid>
    </List>
  );
}

export function QueueCreate() {
  return (
    <Create redirect="show">
      <SimpleForm>
        <TextInput source="name" required fullWidth />
      </SimpleForm>
    </Create>
  );
}

export function QueueEdit() {
  return (
    <Edit mutationMode="pessimistic">
      <SimpleForm>
        <TextInput source="name" required fullWidth />
      </SimpleForm>
    </Edit>
  );
}

export function QueueShow() {
  return (
    <Show>
      <SimpleShowLayout>
        <TextField source="id" />
        <TextField source="name" />
        <DateField source="created_at" showTime />
        <DateField source="updated_at" showTime />
        <ReferenceManyField reference="tasks" target="queue_id" label="Tasks">
          <Datagrid rowClick="show" bulkActionButtons={false}>
            <TextField source="id" />
            <TextField source="type" />
            <TextField source="status" />
            <TextField source="attempts" />
            <DateField source="created_at" showTime />
            <ShowButton />
          </Datagrid>
        </ReferenceManyField>
      </SimpleShowLayout>
    </Show>
  );
}

