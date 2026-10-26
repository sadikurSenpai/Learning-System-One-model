"""Endpoints for score (ordered scale) questions.

- POST /score/ask             generic: bring your own scale (JSON body)
- GET  /score/urgency         use case: triage (query params)
- GET  /score/sentiment       use case: review analytics (query params)
- POST /score/answer-quality  use case: grade an answer, structured state (JSON body)
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from jev.app.client import State, ask_jev, usage_of
from jev.app.score import use_cases
from jev.app.score.schemas import Level, ScoreQuestion, ScoreRequest, ScoreResult

router = APIRouter()


async def ask_score(state: State, question: ScoreQuestion) -> ScoreResult:
    """Send a single score question and describe where the answer lands."""
    raw = await ask_jev(state, {"answer": question.to_api()})
    # A score answer looks like
    # {"type": "score", "score": 2.94, "confidence": 0.94,
    #  "probabilities": {"0": 0, ..., "3": 0.94}, "legend": {"0": "Within a month", ...}}
    # Note the probability keys are indexes as STRINGS.
    answer = raw["answers"]["answer"]

    levels = [
        Level(index=i, label=label, probability=answer["probabilities"].get(str(i), 0.0))
        for i, label in enumerate(question.criteria)
    ]
    score = answer["score"]

    # Split check: are the two most likely levels far apart and both substantial?
    first, second = sorted(levels, key=lambda lv: lv.probability, reverse=True)[:2]
    split = abs(first.index - second.index) > 1 and second.probability >= 0.25

    return ScoreResult(
        score=score,
        max_score=len(levels) - 1,
        nearest=levels[round(score)],
        levels=levels,
        confidence=answer["confidence"],
        split=split,
        usage=usage_of(raw),
    )


@router.post("/ask", response_model=ScoreResult)
async def ask(body: ScoreRequest) -> ScoreResult:
    """Place any state on your own ordered scale."""
    return await ask_score(body.state, body)


@router.get("/urgency", response_model=ScoreResult)
async def urgency(
    text: str = Query(
        description="A customer message",
        examples=["Our whole team is locked out and we have a client demo in 30 minutes!"],
    ),
) -> ScoreResult:
    """How fast should a human respond? 0 = within a month ... 3 = within an hour."""
    return await ask_score({"customer_message": text}, use_cases.URGENCY)


@router.get("/sentiment", response_model=ScoreResult)
async def sentiment(
    text: str = Query(
        description="A customer review",
        examples=["Setup was painful, but support was great and it works fine now."],
    ),
) -> ScoreResult:
    """How positive is the review? 0 = very negative ... 4 = very positive.

    Mixed reviews are a good experiment: watch whether the probability spreads
    over neighbouring levels (a real "it's in between") or splits far apart.
    """
    return await ask_score({"review": text}, use_cases.SENTIMENT)


class QuestionAnswer(BaseModel):
    question: str = Field(examples=["What is the capital of Australia?"])
    answer: str = Field(examples=["Sydney is the capital and largest city of Australia."])


@router.post("/answer-quality", response_model=ScoreResult)
async def answer_quality(body: QuestionAnswer) -> ScoreResult:
    """Grade an answer from 0 (wrong) to 3 (excellent): a cheap LLM-as-judge.

    Jev can only judge with what it knows. For facts it can't check, give it the
    reference material in the state as well.
    """
    return await ask_score(body.model_dump(), use_cases.ANSWER_QUALITY)
