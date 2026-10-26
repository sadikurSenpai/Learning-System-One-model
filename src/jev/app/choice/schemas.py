"""Request and response models for `choice` (pick one option) questions.

A choice question asks "which one of these options?". Jev returns the most
likely option plus a probability for every option. See README section 6.
"""

from typing import Any

from pydantic import BaseModel, Field

from jev.app.client import JevUsage, State


class ChoiceQuestion(BaseModel):
    """One pick-one question, in the shape the Decisions API expects."""

    instructions: str = Field(description="The question itself, in plain language.")
    # The keys are the labels you get back; the values tell Jev when each label applies.
    # Keep options mutually exclusive and add a catch-all like "other".
    criteria: dict[str, str] = Field(min_length=2, description="Option name -> when it applies.")

    def to_api(self) -> dict[str, Any]:
        return {"type": "choice", **self.model_dump()}


class ChoiceRequest(ChoiceQuestion):
    """Body for the generic POST /choice/ask endpoint."""

    state: State = Field(description="What to judge: a string, JSON object or array.")
    min_margin: float = Field(
        0.2, ge=0, le=1, description="Flag for review when the top two options are closer than this."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "Bonjour, je n'arrive pas à me connecter à mon compte.",
                "instructions": "Which language is the message written in?",
                "criteria": {
                    "english": "The message is in English.",
                    "french": "The message is in French.",
                    "spanish": "The message is in Spanish.",
                    "other": "Any other language, or a mix of languages.",
                },
                "min_margin": 0.2,
            }
        }
    }


class ChoiceResult(BaseModel):
    choice: str = Field(description="The most likely option.")
    confidence: float = Field(description="How concentrated the distribution is. Not a safety signal.")
    probabilities: dict[str, float] = Field(description="Every option, most likely first.")
    runner_up: str = Field(description="The second most likely option.")
    margin: float = Field(description="P(choice) - P(runner_up). Small margin = two options compete.")
    needs_review: bool = Field(description="True when margin < min_margin.")
    usage: JevUsage
