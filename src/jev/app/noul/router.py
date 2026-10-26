"""Endpoints for noul (yes / no) questions.

- POST /noul/ask            generic: bring your own question (JSON body)
- GET  /noul/refund-request  use case: support triage (query params)
- GET  /noul/contains-pii    use case: guardrail (query params)
- POST /noul/tool-approval   use case: agent safety with structured state (JSON body)
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from jev.app.client import State, ask_jev, usage_of
from jev.app.noul import use_cases
from jev.app.noul.schemas import Bands, NoulQuestion, NoulRequest, NoulResult

router = APIRouter()


async def ask_noul(state: State, question: NoulQuestion, bands: Bands) -> NoulResult:
    """Send a single noul question and convert the answer into a verdict."""
    raw = await ask_jev(state, {"answer": question.to_api()})
    # A noul answer looks like {"type": "noul", "noul": 0.56}
    probability = raw["answers"]["answer"]["noul"]
    return NoulResult(
        probability=probability,
        verdict=bands.verdict(probability),
        bands=bands,
        usage=usage_of(raw),
    )


def make_bands(yes_at: float, no_below: float) -> Bands:
    """Build Bands from query params; a bad combination becomes a 422, not a 500."""
    try:
        return Bands(yes_at=yes_at, no_below=no_below)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False, include_context=False))


@router.post("/ask", response_model=NoulResult)
async def ask(body: NoulRequest) -> NoulResult:
    """Ask any yes/no question about any state."""
    return await ask_noul(body.state, body, body)


@router.get("/refund-request", response_model=NoulResult)
async def refund_request(
    text: str = Query(
        description="A customer message",
        examples=["I was charged twice this month. Please fix this ASAP."],
    ),
    yes_at: float = Query(0.7, ge=0, le=1),
    no_below: float = Query(0.3, ge=0, le=1),
) -> NoulResult:
    """Is the customer asking for money back?

    Try "charged twice, please fix this" (implied, so expect 'review') against
    "please refund the duplicate charge" (explicit, so expect 'yes').
    """
    return await ask_noul(
        {"customer_message": text}, use_cases.REFUND_REQUEST, make_bands(yes_at, no_below)
    )


@router.get("/contains-pii", response_model=NoulResult)
async def contains_pii(
    text: str = Query(
        description="Any text to screen before storing or sending it",
        examples=["Contact Sarah Lee at sarah.lee@gmail.com or +1 415 555 0134."],
    ),
    # A leak is expensive and a false alarm is cheap, so block earlier than the defaults
    yes_at: float = Query(0.5, ge=0, le=1),
    no_below: float = Query(0.2, ge=0, le=1),
) -> NoulResult:
    """Does the text contain personal data? A guardrail with stricter bands."""
    return await ask_noul(text, use_cases.CONTAINS_PII, make_bands(yes_at, no_below))


class ToolCall(BaseModel):
    tool: str = Field(examples=["sql.execute"])
    arguments: dict[str, Any] = Field(examples=[{"query": "DELETE FROM users WHERE last_login < '2024-01-01'"}])


@router.post("/tool-approval", response_model=NoulResult)
async def tool_approval(call: ToolCall) -> NoulResult:
    """Does this proposed agent tool call need a human's approval?

    The whole tool call is sent as structured JSON state; named fields help Jev
    tell the tool name and its arguments apart.
    """
    return await ask_noul(call.model_dump(), use_cases.TOOL_NEEDS_APPROVAL, Bands())
