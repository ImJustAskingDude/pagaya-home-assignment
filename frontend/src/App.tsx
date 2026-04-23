import AssignmentIcon from "@mui/icons-material/Assignment";
import QueueIcon from "@mui/icons-material/Queue";
import { Admin, Resource } from "react-admin";

import { dataProvider } from "./dataProvider";
import { QueueCreate, QueueEdit, QueueList, QueueShow } from "./resources/queues";
import { TaskCreate, TaskList, TaskShow } from "./resources/tasks";

export function App() {
  return (
    <Admin dataProvider={dataProvider} title="Queue Manager">
      <Resource
        name="queues"
        list={QueueList}
        create={QueueCreate}
        edit={QueueEdit}
        show={QueueShow}
        icon={QueueIcon}
      />
      <Resource name="tasks" list={TaskList} create={TaskCreate} show={TaskShow} icon={AssignmentIcon} />
    </Admin>
  );
}

