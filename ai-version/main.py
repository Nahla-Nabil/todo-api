from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    description="A small CRUD API for managing a to-do list, backed by SQLite.",
    version="2.0",
)

DB_FILE = "tasks.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    (count,) = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy milk", 0),
                ("Walk the dog", 0),
                ("Learn FastAPI", 1),
            ],
        )
        conn.commit()
    conn.close()


init_db()


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the task")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class Task(BaseModel):
    id: int
    title: str
    done: bool


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


@app.get("/tasks", response_model=list[Task], summary="List all tasks")
def get_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


@app.post("/tasks", response_model=Task, status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)", (task.title, 0)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return row_to_task(row)


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, update: TaskUpdate):
    if update.title is not None and not update.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    done_value = None if update.done is None else int(update.done)
    conn = get_db()
    cursor = conn.execute(
        """
        UPDATE tasks
        SET title = COALESCE(?, title), done = COALESCE(?, done)
        WHERE id = ?
        """,
        (update.title, done_value, task_id),
    )
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_db()
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
