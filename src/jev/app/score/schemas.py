"""Request and response models for `score` (ordered scale) questions.

A score question asks "where does this fall on an ordered scale?". Jev returns
a probability for every level and a probability-weighted position:

    score = sum(index * probability)    e.g. 2*0.06 + 3*0.94 = 2.94

See README section 7.
"""

from typing import Any

from pydantic import BaseModel, Field

from jev.app.client import JevUsage, State


class ScoreQuestion(BaseModel):
    """One ordered-scale question, in the shape the Decisions API expects."""

    instructions: str = Field(description="The question itself, in plain language.")
    # Order matters: index 0 is the LOWEST level, the last item is the HIGHEST
    criteria: list[str] = Field(min_length=2, description="Scale levels, lowest first.")

    def to_api(self) -> dict[str, Any]:
        return {"type": "score", **self.model_dump()}


class ScoreRequest(ScoreQuestion):
    """Body for the generic POST /score/ask endpoint."""

    state: State = Field(description="What to judge: a string, JSON object or array.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": {
                    "title": "Senior Backend Engineer",
                    "resume": "8 years of Python, led a team of 5, built payment APIs at a fintech.",
                },
                "instructions": "How well does the candidate match the role?",
                "criteria": ["Not a match", "Weak match", "Good match", "Excellent match"],
            }
        }
    }


class Level(BaseModel):
    index: int
    label: str
    probability: float


class ScoreResult(BaseModel):
    score: float = Field(description="Probability-weighted position on the scale (can be fractional).")
    max_score: int = Field(description="Index of the highest level, so score / max_score is in 0..1.")
    nearest: Level = Field(description="The level closest to the score.")
    levels: list[Level] = Field(description="Every level with its probability, lowest first.")
    confidence: float = Field(description="How concentrated the distribution is.")
    split: bool = Field(
        description="True when two NON-adjacent levels both get >= 25%, e.g. 'trivial or critical'. "
        "The score then lands in the middle and is misleading on its own."
    )
    usage: JevUsage
