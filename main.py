from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import auth
import cache
import db

app = FastAPI()
db.init_db()
cache.ping_with_retry()
auth.ping()


class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

class SignupRequest(BaseModel):
    # Optional with a None default (not a bare `str`) so a missing field is
    # a normal 400 with a JSON body, not FastAPI's automatic 422.
    email: str | None = None
    password: str | None = None

class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


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

@app.post("/auth/signup", status_code=201)
def signup(body: SignupRequest):
    if not body.email or not body.password:
        return JSONResponse(status_code=400, content={"error": "email and password are required"})
    try:
        result = auth.sign_up(body.email, body.password)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    user = result.user
    return JSONResponse(
        status_code=201,
        content={"id": user.id, "email": user.email, "created_at": str(user.created_at)},
    )

@app.post("/auth/login")
def login(body: LoginRequest):
    if not body.email or not body.password:
        return JSONResponse(status_code=400, content={"error": "email and password are required"})
    try:
        result = auth.sign_in(body.email, body.password)
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
    }
