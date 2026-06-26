# AGENTS.md — Cafe Order System

## Project overview

Internal cafe ordering REST API built with **FastAPI + SQLAlchemy + Pydantic**.
Korean-language domain (menu names, descriptions, error messages may be in Korean).

### Layer architecture

```
Router (app/routes/)  →  Service (app/services/)  →  Model (app/models.py)
                                                      Schema (app/schemas.py)
```

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Router | `app/routes/<resource>.py` | HTTP handling, input validation, response formatting |
| Service | `app/services/<name>_service.py` | Business logic (price calculation, inventory checks) |
| Model | `app/models.py` | SQLAlchemy ORM models, enums (`MenuCategory`, `OrderStatus`) |
| Schema | `app/schemas.py` | Pydantic request/response DTOs (`*Create`, `*Response`) |
| Database | `app/database.py` | Session factory, `get_db` dependency |

### Data model

```
MenuItem (1) ── (N) OrderItem (N) ── (1) Order (N) ── (1) Customer
```

Order status flow: `PENDING → CONFIRMED → PREPARING → READY → PICKED_UP`
(cancel allowed from PENDING or CONFIRMED only)

## Before writing code

1. **Search existing patterns** — use Codebase Search to find how similar features are implemented (e.g., "how are GET endpoints defined in routes/menu.py?")
2. **Check internal docs** — use Repo Docs to look up API conventions, error formats, and response structures (see `docs/api-guide.md`, `docs/architecture.md`)
3. **Understand the data model** — review `app/models.py` for table relationships and enum values before adding new fields or tables

## Coding conventions

- New endpoints: create `app/routes/<resource>.py` with `APIRouter(prefix="/api/<resource>", tags=["<resource>"])`
- Register the router in `app/main.py` via `app.include_router(<resource>.router)`
- Business logic goes in `app/services/`, not in route handlers
- Request/response DTOs are Pydantic `BaseModel` subclasses in `app/schemas.py` with `model_config = {"from_attributes": True}` on response models
- Database sessions: always use `db: Session = Depends(get_db)` — never call `SessionLocal()` directly in routes
- Errors: raise `HTTPException(status_code=4xx, detail="message")`
- Keep Korean strings for user-facing content (menu names, descriptions); use English for code identifiers

## Verification (inner loop)

After writing code, **always verify before marking the task complete**:

1. **Import check** — run the new module to catch missing imports:
   ```python
   from app.routes.specials import router
   print("imports OK:", [r.path for r in router.routes])
   ```

2. **Schema validation** — test Pydantic models with sample data:
   ```python
   from app.schemas import MenuItemResponse
   item = MenuItemResponse(
       id=1, name="아메리카노", category="coffee",
       price=4500, description="클래식 커피",
       is_available=True, calories=10, allergens=None
   )
   print(item.model_dump_json(indent=2))
   ```

3. **Response format** — confirm JSON matches the existing API pattern:
   ```python
   import json
   response = {"id": 1, "name": "아메리카노", "price": 3500,
                "original_price": 4500, "discount_pct": 22}
   print(json.dumps(response, ensure_ascii=False, indent=2))
   ```

If any step fails, fix the issue and re-run before proceeding.

## IDE support

This file is automatically read by agents in:

| IDE | File read | Notes |
|-----|-----------|-------|
| Cursor | `AGENTS.md` | Also reads `.cursorrules` if present |
| Claude Code | `AGENTS.md` | Also reads `CLAUDE.md` if present |
| OpenCode | `AGENTS.md` | Primary instruction source |
