"""Shared client for OpenRouter's Decisions API.

All three question modules (noul, choice, score) send their questions through
`ask_jev()`. It only knows the envelope of the API (model + state + questions
-> answers + usage); each module knows how to build and read its own type.
"""

from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from jev.app.config import settings

# Jev accepts the state as a plain string, a JSON object, or an array of related context
State = str | dict[str, Any] | list[Any]


class JevUsage(BaseModel):
    """Billing info attached to every response. Only input tokens are billed."""

    model: str  # the dated snapshot that served the request, e.g. typesafe/jev-1.14-20261014
    input_tokens: int
    cost: float | None = None  # USD for this single request


async def ask_jev(state: State, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Send one Decisions request and return the raw JSON response.

    `questions` maps a name you choose to a question definition, e.g.
    {"is_refund": {"type": "noul", "instructions": ..., "criteria": {...}}}.
    All questions in one call are answered independently and in parallel.
    """
    payload = {"model": settings.jev_model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}

    try:
        # A new client per call keeps the example simple; a long-running service
        # would create one AsyncClient at startup and reuse its connection pool.
        async with httpx.AsyncClient(
            base_url=settings.openrouter_base_url, timeout=settings.request_timeout
        ) as client:
            response = await client.post("/decisions", json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach OpenRouter: {exc}") from exc

    if response.is_error:
        # Errors look like {"error": {"code": 400, "message": "..."}}; pass the message through
        # so a bad criteria shape (e.g. noul without "false") is visible to the API caller.
        try:
            message = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = response.text
        raise HTTPException(status_code=response.status_code, detail=f"Jev error: {message}")

    return response.json()


def usage_of(raw: dict[str, Any]) -> JevUsage:
    """Pull the model snapshot and cost out of a raw Decisions response."""
    return JevUsage(model=raw["model"], **raw["usage"])
