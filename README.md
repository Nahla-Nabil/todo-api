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