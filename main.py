import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import db

app = FastAPI()
db.init_db()

DB_FILE = "tasks.db"


def get_connection():
    """Open a new connection to tasks.db.

    row_factory = sqlite3.Row lets us read columns by name (row["title"])
    instead of by position (row[1]), which is much less error-prone.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table if it doesn't exist yet, and seed three
    example tasks only the first time the app ever runs (table empty)."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    row_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if row_count == 0:
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
    title: str

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


def row_to_task(row: sqlite3.Row) -> dict:
    """Turn a sqlite3.Row into the same plain dict shape the API has
    always returned, so the response body never changes."""
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks", summary="List all tasks")
def get_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)", (task.title, 0)
    )
    conn.commit()
    # cursor.lastrowid is the id SQLite just assigned this row.
    new_row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return row_to_task(new_row)

@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Fall back to the existing value for any field the client didn't send.
    new_title = row["title"]
    new_done = row["done"]

    if update.title is not None:
        if not update.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="title cannot be empty")
        new_title = update.title

    if update.done is not None:
        new_done = int(update.done)

    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (new_title, new_done, task_id),
    )
    conn.commit()
    updated_row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    conn.close()
    return row_to_task(updated_row)

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()