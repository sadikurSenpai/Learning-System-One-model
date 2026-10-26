"""Ready-made noul questions. Each one shows a typical place a yes/no decision appears.

Notice the pattern: concrete `true` AND `false` criteria that describe the boundary.
"""

from jev.app.noul.schemas import NoulCriteria, NoulQuestion

# Support triage: route refund requests to the billing queue.
REFUND_REQUEST = NoulQuestion(
    instructions="Is the customer asking for money back?",
    criteria=NoulCriteria(
        true="The customer explicitly requests a refund, chargeback or reversal of a charge.",
        false="The customer does not ask for money to be returned, even if they report a billing problem.",
    ),
)

# Guardrail: stop personal data from leaking into logs or a third-party service.
CONTAINS_PII = NoulQuestion(
    instructions="Does the text contain personally identifiable information?",
    criteria=NoulCriteria(
        true="It contains data that identifies a real person: full name with contact details, "
        "email address, phone number, home address, national ID, passport or card number.",
        false="It contains no such data, or only generic or fictional placeholders like 'John Doe' or 'user@example.com'.",
    ),
)

# Agent safety: should a human approve this tool call before it runs?
# The state here is structured JSON (tool name + arguments), not free text.
TOOL_NEEDS_APPROVAL = NoulQuestion(
    instructions="Should a human review this tool call before it is executed?",
    criteria=NoulCriteria(
        true="The call is destructive or irreversible (deletes, overwrites, drops), moves money, "
        "sends messages to people outside the team, or changes permissions.",
        false="The call only reads data or makes a small, easily reversible change.",
    ),
)
