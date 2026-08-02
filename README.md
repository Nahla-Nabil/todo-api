# Task API

A small CRUD API for managing a to-do list, built with FastAPI. Data is stored in memory (no database yet).

## How to run

1. Clone this repo and enter the folder:
```bash
   git clone https://github.com/Nahla-Nabil/todo-api.git
   cd todo-api
```
2. Create and activate a virtual environment:
```bash
   python3 -m venv venv
   venv\Scripts\Activate.ps1   # Windows PowerShell
```
3. Install dependencies:
```bash
   pip install fastapi uvicorn
```
4. Start the server:
```bash
   uvicorn main:app --reload --port 8000
```
5. Open `http://localhost:8000` in your browser.

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

![Swagger UI screenshot](swagger-screenshot.png)

## AI vs me

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