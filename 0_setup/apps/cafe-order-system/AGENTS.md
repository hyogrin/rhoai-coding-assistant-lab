# AGENTS.md — Cafe Order System

## Project overview

Internal cafe ordering REST API built with **FastAPI + SQLAlchemy + Pydantic**.

Main structure:

```text
app/routes/     HTTP endpoints
app/services/   Business logic
app/models.py   SQLAlchemy models
app/schemas.py  Pydantic schemas
app/database.py Database session
```

## Working guidelines

* Follow existing code patterns and project structure.
* Read only the files necessary for the requested task.
* For simple tasks, make the requested change directly without extensive analysis or review.
* Do not inspect unrelated files unless required to complete the task.
* Do not make unrelated changes.
* Keep Korean user-facing text and use English for code identifiers.

## Verification

Verify only what is necessary for the requested change.

For documentation-only changes such as updating `README.md`, no code execution or full project review is required.
