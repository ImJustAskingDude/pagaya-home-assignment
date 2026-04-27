from pydantic import BaseModel


class WorkerRead(BaseModel):
    id: str
    name: str
    status: str
    active: int
    reserved: int
    scheduled: int
    registered: int
    processed: int | None
    pid: int | None
    concurrency: int | None
    queues: list[str]
