# Task API

A small CRUD API for managing a to-do list, built with FastAPI. Data is stored in a containerized **PostgreSQL** database, started together with the app by a single `docker compose up`.

## Database

- **Why Postgres in Docker:** the API has now been swapped onto three different storage engines — in-memory (A1), a SQLite file (A2), and now a real Postgres server (A3) — and the routes never changed. That's the point: storage is just an implementation detail behind one small module. Postgres is the same relational engine behind most real production backends, and Docker means no local Postgres install, no version fights — `docker run`/`docker compose up` and a real database server appears on `localhost`.
- **The repository module:** every single line of SQL in this project lives in [`db.py`](db.py) — `main.py`'s routes only ever call `db.list_tasks()`, `db.get_task()`, `db.create_task()`, `db.update_task()`, `db.delete_task()`. Swapping storage again in the future would only touch this one file.
- **Connection & secrets:** the app reads a `DATABASE_URL` connection string from a `.env` file (git-ignored — never committed) via `python-dotenv`. A `.env.example` with placeholder values is committed instead, so anyone cloning the repo knows exactly which variable to set. No password is ever hardcoded in the app code.
- **Schema & seeding:** on startup, `db.init_db()` runs `CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, title TEXT NOT NULL, done BOOLEAN NOT NULL DEFAULT FALSE)`, then seeds the same three example tasks as before — but only if the table is empty, so restarting the app (or the container) never duplicates them. Because `docker compose`'s `depends_on` only waits for the database *container* to start, not for Postgres to finish accepting connections, `init_db()` also retries the first connection a few times before giving up — otherwise the API container could crash on the very first `docker compose up`.
- **Queries:** every query uses **parameterized placeholders** (`%s`, values passed separately via `psycopg`) for every `SELECT`/`INSERT`/`UPDATE`/`DELETE` — never string-formatted SQL.
- **Persistence:** Postgres's data directory is mounted to a named Docker **volume** (`taskdata`), so tasks survive a full `docker compose down` + `docker compose up` — verified by creating a task, tearing the whole stack down, bringing it back up, and confirming the task was still there.

### Explored with psql

Opened a SQL prompt directly inside the database container and ran a query by hand:

```sql
docker exec -it <db-container-name> psql -U postgres -d tasks -c "\dt"
docker exec -it <db-container-name> psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

![psql — tasks table](screenshots/postgres-tasks.png)
<!-- TODO: replace the line above with an actual screenshot of the psql output above, saved as screenshots/postgres-tasks.png (or a GUI like pgAdmin/DBeaver/TablePlus showing the tasks table) -->

## How to run

**The one-command way (recommended):**

1. Clone this repo and enter the folder:
```bash
   git clone https://github.com/Nahla-Nabil/todo-api.git
   cd todo-api
```
2. Copy the example env file (only needed if you plan to also run the app outside of Docker — `compose.yaml` sets its own `DATABASE_URL` for the containerized run):
```bash
   cp .env.example .env
```
3. Start everything — the API and its Postgres database:
```bash
   docker compose up --build
```
4. Open `http://localhost:8000` in your browser. The `tasks` table and three example tasks are created automatically on first run.

**Running locally against a standalone Postgres container** (useful while developing without rebuilding the image each time):

1. Start Postgres by itself, with a volume so data persists:
```bash
   docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5433:5432 -v taskdata:/var/lib/postgresql/data -d postgres:16
```
   (Host port `5433` is used instead of the default `5432` here because a native Postgres install can already be sitting on `5432` on some machines — adjust to `5432` if that's free on yours, and update `.env`/`.env.example` to match.)
2. Create a virtual environment and install dependencies:
```bash
   python3 -m venv venv
   venv\Scripts\Activate.ps1   # Windows PowerShell
   pip install -r requirements.txt
```
3. Make sure `.env` has `DATABASE_URL=postgresql://postgres:dev@localhost:5433/tasks`, then start the server:
```bash
   uvicorn main:app --reload --port 8000
```

## Endpoints

| Method | Path             | Description                  |
|--------|------------------|-------------------------------|
| GET    | /                | API info                     |
| GET    | /health          | Health check                 |
| GET    | /tasks           | List all tasks                |
| GET    | /tasks/{id}      | Get a single task             |
| POST   | /tasks           | Create a new task              |
| PUT    | /tasks/{id}      | Update a task                 |
| DELETE | /tasks/{id}      | Delete a task                 |

## Example request

```bash
curl.exe -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{`"title`":`"Read a book`"}"
```

Response:
```json
{
  "id": 4,
  "title": "Read a book",
  "done": false
}
```

## Swagger UI

Interactive docs are available at `http://localhost:8000/docs`.

![Swagger UI screenshot](screenshots/swagger-screenshot.png)

## AI vs me — Assignment 1 (in-memory API)

**Prompt used:**
> Build this inside the ai-version/ folder only, don't touch main.py: Build a REST API using Python and FastAPI. It needs these 5 endpoints: GET /tasks, GET /tasks/{id}, POST /tasks, PUT /tasks/{id}, and DELETE /tasks/{id}. When creating a task, return status code 201. When deleting, return status code 204. If the title is empty, return status code 400 with an error message. If a task id doesn't exist, return status code 404. Store the tasks in memory, no database needed. Also add Swagger UI documentation.

**What the AI did better:**
The AI used Pydantic's `response_model` (a `Task` schema) on every endpoint instead of returning plain dicts, which makes the Swagger docs show the exact response shape. It also factored out a shared `find_task()` helper instead of repeating the same lookup loop in every endpoint — cleaner and less repetitive than my version.

**What it got wrong or ignored:**
My prompt never mentioned `GET /` or `GET /health`, so the AI's version doesn't have them at all — it only built exactly the 5 endpoints I listed, nothing more. It also worded the validation error message differently ("title cannot be empty" vs. my "title is required") since I never specified exact wording.

**What my prompt forgot to specify — and what the AI silently decided:**
I didn't specify how new task IDs should be generated, so the AI used a global `next_id` counter starting at 4, while I had computed `max(id) + 1` dynamically. Both work, but they'd behave differently if a task were ever deleted and a new one created after. I also never asked for a Field description or an app title/description in the FastAPI() constructor — the AI added those on its own for nicer-looking docs.

**One rematch:**
I'd improve the prompt by explicitly asking for `GET /` and `/health` endpoints, and specifying that new IDs should reuse the `max(existing_ids) + 1` logic to match my original behavior exactly.

## AI vs me — Assignment 2 (SQLite migration, Stage 6)

**Prompt used:**
> Migrate the API in ai-version/main.py (the AI version from Assignment 1) from the in-memory list to SQLite. Keep everything inside ai-version/ — don't touch the root main.py. Use Python's built-in sqlite3 module (no ORM) and a file called tasks.db. On startup, create a `tasks` table if it doesn't already exist, with columns id (integer primary key), title (text), and done (boolean). Seed three example tasks — "Buy milk" (not done), "Walk the dog" (not done), "Learn FastAPI" (done) — but only if the table is empty, so restarting the app never duplicates them. Every endpoint must keep exactly the same behaviour as before: GET /tasks, GET /tasks/{id}, POST /tasks (201, or 400 if title is missing/empty), PUT /tasks/{id} (200, partial updates allowed, 404 if the id doesn't exist), DELETE /tasks/{id} (204, or 404 if the id doesn't exist). All queries must use parameterized placeholders (?) — never build SQL by pasting values into the string.

**What the AI did better:**
For `PUT`, the AI used a single `UPDATE tasks SET title = COALESCE(?, title), done = COALESCE(?, done) WHERE id = ?` query and read `cursor.rowcount` to detect a missing id. My version does a `SELECT` first to check the row exists, then a separate `UPDATE` — the AI's approach is one round trip to the database instead of two, for the same result.

**What it got wrong or ignored:**
The AI validated the create-task title only with Pydantic's `Field(..., min_length=1)`, no manual `.strip()` check. `min_length=1` blocks `""` but not whitespace like `"   "` — so `POST /tasks` with `{"title": "   "}` returned **201 Created** with a blank-looking task instead of the `400` my prompt asked for. I confirmed this by actually running the endpoint (see below); it's exactly the kind of edge case that's easy to miss when you only skim generated code instead of testing it. Interestingly, the AI *did* add a correct `.strip()` check on the `PUT` endpoint — so the same validation rule was enforced inconsistently between two endpoints of the same file.

```
$ curl -X POST /tasks -d '{"title": "   "}'
→ before fix: 201 Created  {"id": 5, "title": "   ", "done": false}
→ after fix:  400 Bad Request  {"detail": "Title cannot be empty"}
```

**What my prompt forgot to specify — and what the AI silently decided:**
I never said whether `done` should be stored as `BOOLEAN` or `INTEGER` in the `CREATE TABLE` statement — SQLite doesn't actually have a boolean type (it stores `0`/`1` either way), so the AI picked `INTEGER NOT NULL DEFAULT 0`, which is arguably the more accurate column type since it names what SQLite actually stores. I also never said anything about response docs, and the AI added a `Task` Pydantic model, a `FastAPI(title=..., description=..., version=...)` constructor, and `summary=` text on every route purely for nicer-looking `/docs` output — none of which I asked for.

**One rematch:**
I added one sentence to the prompt — *"reject titles that are empty or contain only whitespace on both POST and PUT, not just missing"* — regenerated the `create_task` validation, and it now correctly returns `400` for a whitespace-only title (shown above), matching `PUT`'s behavior.