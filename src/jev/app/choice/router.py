"""Endpoints for choice (pick one option) questions.

- POST /choice/ask          generic: bring your own options (JSON body)
- GET  /choice/ticket-team  use case: route a support ticket (query params)
- GET  /choice/intent       use case: branch a workflow on visitor intent (query params)
"""

from fastapi import APIRouter, Query

from jev.app.choice import use_cases
from jev.app.choice.schemas import ChoiceQuestion, ChoiceRequest, ChoiceResult
from jev.app.client import State, ask_jev, usage_of

router = APIRouter()


async def ask_choice(state: State, question: ChoiceQuestion, min_margin: float) -> ChoiceResult:
    """Send a single choice question and rank the options. """
    raw = await ask_jev(state, {"answer": question.to_api()})
    # A choice answer looks like
    # {"type": "choice", "choice": "billing", "confidence": 1, "probabilities": {"billing": 1, ...}}
    answer = raw["answers"]["answer"]

    ranked = dict(sorted(answer["probabilities"].items(), key=lambda kv: kv[1], reverse=True))
    (_, top_p), (runner_up, second_p) = list(ranked.items())[:2]
    margin = round(top_p - second_p, 4)

    return ChoiceResult(
        choice=answer["choice"],
        confidence=answer["confidence"],
        probabilities=ranked,
        runner_up=runner_up,
        margin=margin,
        needs_review=margin < min_margin,
        usage=usage_of(raw),
    )


@router.post("/ask", response_model=ChoiceResult)
async def ask(body: ChoiceRequest) -> ChoiceResult:
    """Pick one of your own options for any state."""
    return await ask_choice(body.state, body, body.min_margin)


@router.get("/ticket-team", response_model=ChoiceResult)
async def ticket_team(
    text: str = Query(
        description="A support ticket",
        examples=["The dashboard shows a blank page after I log in, and I'm also double billed."],
    ),
    min_margin: float = Query(0.2, ge=0, le=1),
) -> ChoiceResult:
    """Which team owns this ticket?

    A ticket that mixes two problems (a bug AND a billing issue) shows up as a small
    margin between the top two teams, which is when a human should triage it.
    """
    return await ask_choice({"ticket": text}, use_cases.TICKET_TEAM, min_margin)


@router.get("/intent", response_model=ChoiceResult)
async def intent(
    text: str = Query(
        description="A message from a website visitor",
        examples=["How much would it cost for 200 seats with SSO?"],
    ),
    min_margin: float = Query(0.2, ge=0, le=1),
) -> ChoiceResult:
    """What does the visitor want: buy, support, cancel or browse?"""
    return await ask_choice({"visitor_message": text}, use_cases.INTENT, min_margin)
