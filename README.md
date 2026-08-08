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

## Extras

A few optional stretch goals from the assignment, done after the core 6 stages:

**A real health check.** `GET /health` doesn't just report "the process is alive" — it runs `SELECT 1` against Postgres via `db.ping()`. If that fails, it returns `503` with `{"status": "degraded", "db": "error"}` instead of a plain `200`. This matters because a load balancer polling `/health` can pull an instance out of rotation the moment its database connection goes bad, instead of continuing to route real traffic to a server that can't actually serve it.

**An index on `tasks.done`, and a genuinely surprising `EXPLAIN ANALYZE`.** Bulk-seeded the table with 200,000 extra rows to make a difference measurable, then compared `EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = true`:

| Step | Plan | Execution time |
|---|---|---|
| Before the index | Seq Scan | 8.78 ms |
| After `CREATE INDEX`, before `ANALYZE` | **Still Seq Scan** | 8.72 ms |
| After running `ANALYZE tasks` | Bitmap Index Scan | **4.48 ms** |

Creating the index alone didn't change anything — Postgres's query planner was still working off stale statistics from before the index existed, so it kept picking a sequential scan. Only after `ANALYZE` refreshed those statistics did the planner realize the index was worth using, roughly halving execution time. The index (`idx_tasks_done`) is now created automatically in `db.init_db()`; the 200k test rows were deleted afterward — the seeded table still only has the original 3 tasks.

**A multi-stage Dockerfile.** Split the build into a `builder` stage that installs dependencies into `/install`, and a final stage that only copies that installed prefix plus the two source files — no pip cache, build metadata, or intermediate layers carried into the final image. Went from **240MB → 227MB**. The reduction is modest here since the original Dockerfile already used `--no-cache-dir` and never needed extra build tools (`psycopg[binary]` ships prebuilt wheels) — the main win of multi-stage builds shows up more when a project actually needs a compiler toolchain to build dependencies.

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

## AI vs me — Assignment 3 (Postgres/Docker migration)

**Prompt used:**
> Containerize main.py — the hand-written Python/FastAPI version — onto Postgres, using psycopg. Everything lives in a new ai-version/ folder. Don't touch the root main.py or db.py. Startup connects to Postgres using a DATABASE_URL from .env — password never hardcoded. Create the tasks table if it's not there yet: id serial primary key, title text, done boolean. Seed the same three tasks as before ("Buy milk" and "Walk the dog" not done, "Learn FastAPI" done), but only when the table's empty — restarting the app shouldn't add them again. Endpoints need to behave exactly like they do now: GET /tasks, GET /tasks/{id} (404 if missing), POST /tasks (201, or 400 for missing/empty title), PUT /tasks/{id} (200, partial updates fine, 404 if the id's not there), DELETE /tasks/{id} (204, or 404 if missing). Queries stay parameterized with %s placeholders — no pasting values into SQL strings. Write a Dockerfile and docker-compose.yml that bring up the app and Postgres together with a named volume, so data survives a restart.

**What the AI did better:**
Same trick as Assignment 2's AI: `PUT` uses a single `UPDATE ... SET title = COALESCE(%s, title), done = COALESCE(%s, done) ... RETURNING *`, and `DELETE` reads `cursor.rowcount` instead of doing a `SELECT` first — one round trip instead of two, for both. It also added `response_model=Task` on every route for nicer `/docs` output, which I didn't ask for.

**What it got wrong or ignored:**
1. **The exact same whitespace-title bug as Assignment 2, again.** `POST /tasks` only validates with `Field(..., min_length=1)`, no `.strip()` — so `{"title": "   "}` returns `201 Created` instead of `400`. `PUT` gets a correct manual `.strip()` check, so the same inconsistency between the two endpoints repeated itself almost exactly, in a brand-new file, on a completely different prompt.
```
$ curl -X POST /tasks -d '{"title": "   "}'
→ 201 Created  {"id": 4, "title": "   ", "done": false}
```
2. **`docker-compose.yml` used an obsolete `version: "3.9"` key** — Compose printed a deprecation warning on every `up`/`down`. My own `compose.yaml` doesn't have this line at all.
3. **No connection-retry logic at startup.** My `db.init_db()` retries the first Postgres connection a few times, because `depends_on` only waits for the *container* to start, not for Postgres itself to finish accepting connections. The AI's `init_db()` makes one bare connection attempt — it happened to work here because the Postgres image was already cached and started fast, but that's luck, not a guarantee; a slower first pull could crash it on the very first `docker compose up`.
4. **Defaulted to host port 8000 with no awareness of my machine.** My own stack was already running on 8000, so `docker compose up` failed outright the first time (`port is already allocated`) until I stopped my own stack to test the AI's. Not really the AI's fault — it can't know what's already running locally — but it's a reminder that "works first try" depends on context an AI never has.

**What my prompt forgot to specify — and what the AI silently decided:**
I never said what the Postgres username/password should default to, so the AI picked `postgres`/`postgres` — different from my own `dev` default, so the two `.env.example` files don't actually match each other even though they solve the same problem. I also never mentioned `GET /` or `/health` (only the 5 CRUD routes), so — exactly like Assignment 1 — the AI built only what I explicitly listed and nothing more. And I never said whether the DB code should live in its own module: the AI put everything straight into `main.py`, while I split mine into `db.py` — my prompt never actually asked for a "repository module" the way the real assignment brief did.

**One rematch:**
I'd add: *"reject titles that are empty or whitespace-only on both POST and PUT, not just missing — and retry the first database connection a few times at startup, since the app container may start before Postgres is ready to accept connections."*