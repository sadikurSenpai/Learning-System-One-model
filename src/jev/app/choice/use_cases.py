"""Ready-made choice questions. Each option describes the boundary to its neighbours."""

from jev.app.choice.schemas import ChoiceQuestion

# Routing: send a support ticket to the team that owns it.
TICKET_TEAM = ChoiceQuestion(
    instructions="Which team should handle this support ticket?",
    criteria={
        "billing": "Charges, invoices, refunds, subscriptions, payment processing or checkout failures.",
        "technical": "Bugs, crashes, errors, slow performance, rendering or integration issues.",
        "account": "Login, password reset, two-factor authentication, profile or team permissions.",
        "other": "Feature requests, general questions or anything the teams above do not own.",
    },
)

# Workflow branching: what does the visitor want to do?
INTENT = ChoiceQuestion(
    instructions="What is the main intent of this message from a website visitor?",
    criteria={
        "buy": "They want to purchase, upgrade, get a quote or talk to sales.",
        "support": "They already use the product and need help with a problem.",
        "cancel": "They want to cancel, downgrade or close their account.",
        "browse": "They are just exploring, comparing or asking general questions about the product.",
    },
)
