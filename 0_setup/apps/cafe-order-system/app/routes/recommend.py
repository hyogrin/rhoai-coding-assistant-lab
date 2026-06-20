import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MenuItem

router = APIRouter(prefix="/api/recommend", tags=["recommend"])

MODEL_ENDPOINT = os.getenv("MODEL_ENDPOINT", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MAAS_API_KEY = os.getenv("MAAS_API_KEY", "")

_tracer = None


def _get_tracer():
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer("cafe-order-system.recommend")
        except Exception:
            pass
    return _tracer


class RecommendResponse(BaseModel):
    recommendation: str
    model: str
    menu_context: list[str]


@router.get("/", response_model=RecommendResponse)
async def get_recommendation(
    mood: str = "anything refreshing",
    db: Session = Depends(get_db),
):
    """Ask the LLM to recommend a menu item based on mood and current menu."""
    if not MODEL_ENDPOINT:
        raise HTTPException(status_code=503, detail="MODEL_ENDPOINT not configured")

    items = db.query(MenuItem).filter(MenuItem.is_available == True).all()  # noqa: E712
    menu_text = ", ".join(f"{i.name} ({i.category.value}, {i.price}원)" for i in items)

    messages = [
        {"role": "system", "content": "You are a friendly cafe barista. Recommend ONE menu item. Be brief (1-2 sentences)."},
        {"role": "user", "content": f"Menu: {menu_text}\n\nI'm in the mood for: {mood}"},
    ]

    tracer = _get_tracer()
    if tracer:
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute("llm.request.model", MODEL_NAME)
        span.set_attribute("llm.request.mood", mood)
        span.set_attribute("llm.menu_items_count", len(items))

    headers = {"Content-Type": "application/json"}
    if MAAS_API_KEY:
        headers["Authorization"] = f"Bearer {MAAS_API_KEY}"

    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        resp = await client.post(
            f"{MODEL_ENDPOINT}/v1/chat/completions",
            headers=headers,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": 100,
                "temperature": 0.7,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"LLM returned {resp.status_code}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    if tracer:
        span = trace.get_current_span()
        span.set_attribute("llm.response.model", data.get("model", MODEL_NAME))
        span.set_attribute("llm.usage.prompt_tokens", usage.get("prompt_tokens", 0))
        span.set_attribute("llm.usage.completion_tokens", usage.get("completion_tokens", 0))
        span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))

    return RecommendResponse(
        recommendation=content,
        model=data.get("model", MODEL_NAME),
        menu_context=[i.name for i in items],
    )
