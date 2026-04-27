import AssignmentIcon from "@mui/icons-material/Assignment";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import MemoryIcon from "@mui/icons-material/Memory";
import QueueIcon from "@mui/icons-material/Queue";
import { Admin, Resource } from "react-admin";

import { AppLayout } from "./components/AppLayout";
import { NotificationCenterProvider } from "./components/NotificationCenter";
import { dataProvider } from "./dataProvider";
import { QueueCreate, QueueEdit, QueueList, QueueShow } from "./resources/queues";
import { TaskCreate, TaskList, TaskResultList, TaskShow } from "./resources/tasks";
import { WorkerList } from "./resources/workers";

export function App() {
  return (
    <NotificationCenterProvider>
      <Admin dataProvider={dataProvider} layout={AppLayout} title="Queue Manager">
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
        <Resource name="workers" list={WorkerList} icon={MemoryIcon} />
      </Admin>
    </NotificationCenterProvider>
  );
}
