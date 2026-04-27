import AssignmentIcon from "@mui/icons-material/Assignment";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import QueueIcon from "@mui/icons-material/Queue";
import { Admin, Resource } from "react-admin";

import { dataProvider } from "./dataProvider";
import { QueueCreate, QueueEdit, QueueList, QueueShow } from "./resources/queues";
import { TaskCreate, TaskList, TaskResultList, TaskShow } from "./resources/tasks";

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
      <Resource
        name="task-results"
        list={TaskResultList}
        icon={FactCheckIcon}
        options={{ label: "Task Results" }}
      />
    </Admin>
  );
}
