from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    description="A small CRUD API for managing a to-do list. Data is stored in memory.",
    version="1.0",
)

tasks: list[dict] = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Walk the dog", "done": False},
    {"id": 3, "title": "Learn FastAPI", "done": True},
]
next_id = 4


class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the task")


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


class Task(BaseModel):
    id: int
    title: str
    done: bool


def find_task(task_id: int) -> dict:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/tasks", response_model=list[Task], summary="List all tasks")
def get_tasks():
    return tasks


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    return find_task(task_id)


@app.post(
    "/tasks",
    response_model=Task,
    status_code=201,
    summary="Create a new task",
)
def create_task(task: TaskCreate):
    global next_id
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="title cannot be empty")
    new_task = {"id": next_id, "title": task.title, "done": False}
    tasks.append(new_task)
    next_id += 1
    return new_task


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, update: TaskUpdate):
    task = find_task(task_id)
    if update.title is not None:
        if not update.title.strip():
            raise HTTPException(status_code=400, detail="title cannot be empty")
        task["title"] = update.title
    if update.done is not None:
        task["done"] = update.done
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    task = find_task(task_id)
    tasks.remove(task)
