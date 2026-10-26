"""Ready-made score questions. Levels go from lowest to highest and are clearly distinct."""

from jev.app.score.schemas import ScoreQuestion

# Triage: how fast should a human respond?
URGENCY = ScoreQuestion(
    instructions="How urgently should a human respond to this message?",
    criteria=["Within a month", "Within a week", "Within a day", "Within an hour"],
)

# Analytics: how does the customer feel? (5-point scale, 0 = very negative)
SENTIMENT = ScoreQuestion(
    instructions="What is the overall sentiment of this customer review?",
    criteria=["Very negative", "Negative", "Neutral", "Positive", "Very positive"],
)

# LLM-as-judge, cheaper: grade an answer written by an agent or a model.
# The state is structured JSON (question + answer) so Jev can tell the two apart.
ANSWER_QUALITY = ScoreQuestion(
    instructions="How well does the answer address the question?",
    criteria=[
        "Wrong or off-topic: the answer is incorrect or does not address the question.",
        "Partial: on topic but misses important parts or contains errors.",
        "Good: correct and addresses the question, with minor gaps.",
        "Excellent: correct, complete and directly answers the question.",
    ],
)
