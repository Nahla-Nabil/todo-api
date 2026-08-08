from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import cache
import db

app = FastAPI()
db.init_db()
cache.ping_with_retry()


class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    """Not just "is the process alive" — actually pings Postgres with
    SELECT 1, and Redis with PING. A load balancer polling this can pull
    an instance out of rotation the moment a dependency goes bad, instead
    of routing traffic to a server that can't serve real requests."""
    db_status = "ok"
    try:
        db.ping()
    except Exception:
        db_status = "error"

    redis_status = "ok"
    try:
        cache.ping()
    except Exception:
        redis_status = "error"

    healthy = db_status == "ok" and redis_status == "ok"
    body = {"status": "ok" if healthy else "degraded", "db": db_status, "redis": redis_status}
    return body if healthy else JSONResponse(status_code=503, content=body)

@app.get("/tasks", summary="List all tasks")
def get_tasks():
    return db.list_tasks()

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    row = db.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    return db.create_task(task.title)

@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    row = db.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Fall back to the existing value for any field the client didn't send.
    new_title = row["title"]
    new_done = row["done"]

    if update.title is not None:
        if not update.title.strip():
            raise HTTPException(status_code=400, detail="title cannot be empty")
        new_title = update.title

    if update.done is not None:
        new_done = update.done

    return db.update_task(task_id, new_title, new_done)

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    row = db.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    db.delete_task(task_id)
