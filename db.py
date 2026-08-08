"""The one module that talks to Postgres. Every route in main.py that needs
data calls a function here — nothing outside this file runs SQL."""

import os
import time

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    """Open a new connection to Postgres.

    row_factory=dict_row lets us read columns by name (row["title"])
    instead of by position, the same convenience sqlite3.Row gave us —
    and Postgres's native BOOLEAN means the values already come back as
    real Python bools, no manual casting needed.
    """
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db(retries: int = 10, delay: float = 1.0) -> None:
    """Create the tasks table if it doesn't exist yet, and seed three
    example tasks only the first time the app ever runs (table empty).

    Retries the initial connection because docker compose's
    `depends_on: [db]` only waits for the db container to start, not for
    Postgres to finish accepting connections — without this loop the app
    would crash on the very first `docker compose up`.
    """
    conn = None
    last_error = None
    for _ in range(retries):
        try:
            conn = get_connection()
            break
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    if conn is None:
        raise last_error

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    row_count = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
    if row_count == 0:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                [
                    ("Buy milk", False),
                    ("Walk the dog", False),
                    ("Learn FastAPI", True),
                ],
            )
    conn.commit()
    conn.close()


def ping() -> bool:
    """Run SELECT 1 against Postgres to check it's actually reachable —
    a real health check, not just "is the process alive"."""
    conn = get_connection()
    conn.execute("SELECT 1")
    conn.close()
    return True


def list_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    conn.close()
    return rows


def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    return row


def create_task(title: str):
    conn = get_connection()
    row = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (title, False),
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def update_task(task_id: int, title: str, done: bool):
    conn = get_connection()
    row = conn.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
        (title, done, task_id),
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def delete_task(task_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
