"""Request and response models for `noul` (yes / no) questions.

A noul question asks "does this condition hold?". Jev answers with one number:
the probability that the answer is `true`. See README section 5.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from jev.app.client import JevUsage, State


class NoulCriteria(BaseModel):
    """Describe BOTH sides. The `false` description matters as much as `true`."""

    true: str = Field(description="What it means for the answer to be yes.")
    false: str = Field(description="What it means for the answer to be no.")


class NoulQuestion(BaseModel):
    """One yes/no question, in the shape the Decisions API expects."""

    instructions: str = Field(description="The question itself, in plain language.")
    criteria: NoulCriteria

    def to_api(self) -> dict[str, Any]:
        return {"type": "noul", **self.model_dump()}


class Bands(BaseModel):
    """Turn a probability into an action with two cutoffs instead of one.

        0 ──── no_below ──── yes_at ──── 1
           "no"       "review"      "yes"

    The middle band is where Jev is unsure (e.g. 0.56) and a human should look.
    Pick the cutoffs from the cost of each mistake, not from round numbers.
    """

    yes_at: float = Field(0.7, ge=0, le=1, description="At or above this probability -> yes.")
    no_below: float = Field(0.3, ge=0, le=1, description="Below this probability -> no.")

    @model_validator(mode="after")
    def check_order(self) -> "Bands":
        if self.no_below > self.yes_at:
            raise ValueError("no_below must be less than or equal to yes_at")
        return self

    def verdict(self, probability: float) -> Literal["yes", "no", "review"]:
        if probability >= self.yes_at:
            return "yes"
        if probability < self.no_below:
            return "no"
        return "review"


class NoulRequest(NoulQuestion, Bands):
    """Body for the generic POST /noul/ask endpoint: a question, the state to judge, and the bands."""

    state: State = Field(description="What to judge: a string, JSON object or array.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "state": "Your app has stopped working since yesterday. Cancel my plan and send my money back.",
                "instructions": "Is the customer asking for money back?",
                "criteria": {
                    "true": "The customer requests a refund or reversal of a charge.",
                    "false": "The customer does not ask for money to be returned.",
                },
                "yes_at": 0.7,
                "no_below": 0.3,
            }
        }
    }


class NoulResult(BaseModel):
    probability: float = Field(description="P(answer is true). 0.5 means 'unsure', not 'medium'.")
    verdict: Literal["yes", "no", "review"]
    bands: Bands
    usage: JevUsage
