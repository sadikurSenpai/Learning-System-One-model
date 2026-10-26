# Learning Jev (via OpenRouter)

A hands-on learning repository for **Jev**, TypeSafe AI's *decision model*, called through
OpenRouter's Decisions API and exposed through a small FastAPI service.

The README is the theory. The code under `src/jev/` implements each concept one module at a
time, with comments explaining the *why* and not just the *what*.

---

## Table of contents

1. [What is Jev?](#1-what-is-jev)
2. [Jev vs. an LLM](#2-jev-vs-an-llm)
3. [The mental model: state + questions → typed answers](#3-the-mental-model-state--questions--typed-answers)
4. [Calibration: why the probabilities matter](#4-calibration-why-the-probabilities-matter)
5. [Question type 1 — `noul` (yes / no)](#5-question-type-1--noul-yes--no)
6. [Question type 2 — `choice` (pick one option)](#6-question-type-2--choice-pick-one-option)
7. [Question type 3 — `score` (ordered scale)](#7-question-type-3--score-ordered-scale)
8. [Asking several questions at once](#8-asking-several-questions-at-once)
9. [The raw HTTP API](#9-the-raw-http-api)
10. [Turning probabilities into actions (thresholds)](#10-turning-probabilities-into-actions-thresholds)
11. [When to use Jev — and when not to](#11-when-to-use-jev--and-when-not-to)
12. [Writing good instructions and criteria](#12-writing-good-instructions-and-criteria)
13. [Project setup](#13-project-setup)
14. [Code layout and endpoints](#14-code-layout-and-endpoints)

---

## 1. What is Jev?

Jev is a **hosted classifier**, which TypeSafe calls a *System One* model. You give it some
information and a set of well-defined questions. For every question it returns:

- a **typed answer** (a boolean probability, a chosen option, or a position on a scale), and
- a **probability distribution** over the possible answers, plus a confidence value where it applies.

It **never generates prose**. You get no explanations, chain of thought, or free text, only
structured decisions your code can branch on directly.

Key facts:

| Property        | Value                                                                    |
|-----------------|--------------------------------------------------------------------------|
| Vendor          | TypeSafe AI                                                              |
| Access          | OpenRouter, `POST https://openrouter.ai/api/alpha/decisions`             |
| Model IDs       | `typesafe/jev-1.14` (current), `typesafe/jev-1.13`, `~typesafe/jev-latest` |
| Pricing         | Pay for **input tokens only**; output tokens are free                    |
| Training        | Reinforcement Learning for Calibrated Decisions (RLCD)                   |
| Question types  | `noul`, `choice`, `score` (plus `box` for images, not covered here)      |

> Pinned IDs such as `typesafe/jev-1.14` resolve to a dated snapshot. The response's `model`
> field shows it, e.g. `typesafe/jev-1.14-20261014`.

---

## 2. Jev vs. an LLM

People often use a chat LLM as a classifier, for example: *"Read this ticket and reply with
only one word: billing, technical or account."* That works, but it is the wrong tool:

| Concern                 | Chat LLM used as classifier                            | Jev                                          |
|-------------------------|--------------------------------------------------------|----------------------------------------------|
| Output                  | Free text you must parse (and it may not comply)       | Typed JSON, always in the shape you defined  |
| Probabilities           | Not given, or self-reported ("I'm 90% sure")           | A real distribution over every option        |
| Calibration             | Tuned for *likeable* answers, not honest confidence    | Trained so 0.8 means "right ~80% of the time" |
| Cost                    | Pays for reasoning and output tokens                   | Output is free; only input is billed         |
| Latency                 | Generates token by token                               | One forward decision, much faster            |
| Explanations            | Yes                                                    | **No**; use an LLM if you need one           |
| Multi-step reasoning    | Yes                                                    | **No**                                       |

Jev is not new magic. Classifiers have existed for decades (logistic regression, fastText,
fine-tuned BERT). What Jev adds is that it is **zero-shot**: you define the labels in plain
English at request time, with no training data and no fine-tuning, and you still get
calibrated probabilities.

---

## 3. The mental model: state + questions → typed answers

```
            ┌──────────────────────────────┐
  state ──▶ │                              │ ──▶ answers.<name>.noul         (0..1)
            │             Jev              │ ──▶ answers.<name>.choice       ("billing")
questions ▶ │                              │ ──▶ answers.<name>.score        (2.94)
            └──────────────────────────────┘      + probabilities, confidence
```

- **`state`**: *what* to judge. A plain string, a JSON object, or an array of related context
  (a support ticket, a chat transcript, a proposed tool call, a log excerpt).
  **Jev only knows what is in the state.** If the decision depends on information you did not
  include, Jev cannot know it.
- **`questions`**: *what to decide*. A map from a name you choose (e.g. `"is_refund"`) to a
  question definition with:
  - `type`: `noul`, `choice` or `score`
  - `instructions`: the question itself, in plain language
  - `criteria`: the possible answers and what each one means (the shape depends on the type)
- **`answers`**: one typed answer per question name, in the response.

---

## 4. Calibration: why the probabilities matter

A model is **calibrated** when its probabilities match reality:

> Take every case where the model said "yes, 0.8". About 80% of them should truly be "yes".

This is what makes probabilities **actionable**. With calibrated numbers you can write rules
like:

```python
if answers["is_spam"]["noul"] >= 0.95:
    block()            # very sure, so act automatically
elif answers["is_spam"]["noul"] >= 0.60:
    send_to_review()   # unsure, so ask a human
else:
    allow()
```

Chat LLMs are trained mainly on human preference (RLHF), which rewards *sounding* right, not
*being* calibrated. Jev is trained with **RLCD** (Reinforcement Learning for Calibrated
Decisions), where the reward is honest probabilities.

> Don't take calibration on faith. Section 10 and the roadmap include measuring it on your own
> labelled data.

---

## 5. Question type 1 — `noul` (yes / no)

**Use it for:** "Does this condition hold?" Examples: is this spam, does this contain PII, is
this a refund request, does this tool call need approval.

### Request shape

`criteria` **must** contain both keys `true` and `false`, each describing what that answer means.

```json
"is_refund_request": {
  "type": "noul",
  "instructions": "Is the customer asking for money back?",
  "criteria": {
    "true":  "The customer requests a refund or reversal of a charge.",
    "false": "The customer does not ask for money to be returned."
  }
}
```

### Response shape

```json
"is_refund_request": { "type": "noul", "noul": 0.56 }
```

`noul` is the **probability that the answer is `true`**, between 0 and 1.

### How to read it

| `noul` value | Meaning                                              |
|--------------|------------------------------------------------------|
| ~0.99        | Almost certainly yes                                 |
| ~0.50        | **Uncertain**: yes and no are about equally likely   |
| ~0.01        | Almost certainly no                                  |

> **Common mistake:** 0.5 does **not** mean "medium" or "partially". It means *"I don't know."*
> If you want degrees of something ("how angry is the customer?"), use `score`.

### Real example from this repo

Ticket: *"I was charged twice for my subscription this month and my card was declined on
checkout after that. Please fix this ASAP, I have a client demo tomorrow."*

Jev returned `noul: 0.56` for *"Is the customer asking for money back?"*. This is a good
answer. The customer says they were charged twice and asks to *"fix this"*, but they never
explicitly ask for a refund. They might want a refund, a credit, or just a working card.
Jev's uncertainty reflects a real ambiguity in the text. In production that is exactly the
case to send to a human.

---

## 6. Question type 2 — `choice` (pick one option)

**Use it for:** "Which one of these options?" Examples: routing a ticket to a team, detecting
intent, picking a language, classifying a topic.

### Request shape

`criteria` maps each **option name** (the label you get back) to a **description** of when
that option applies.

```json
"category": {
  "type": "choice",
  "instructions": "Which team should handle this ticket?",
  "criteria": {
    "billing":   "Charges, invoices, refunds, payment processing or checkout failures.",
    "technical": "Bugs, crashes, rendering, performance or integration issues.",
    "account":   "Login, password, profile or permission issues.",
    "other":     "Anything that does not fit the teams above."
  }
}
```

### Response shape

```json
"category": {
  "type": "choice",
  "choice": "billing",
  "probabilities": { "billing": 1, "technical": 0, "account": 0, "other": 0 },
  "confidence": 1
}
```

| Field           | Meaning                                                                |
|-----------------|------------------------------------------------------------------------|
| `choice`        | The most likely option (its key from `criteria`)                       |
| `probabilities` | A probability for **every** option; together they sum to ~1            |
| `confidence`    | How concentrated the distribution is (1 = all mass on a single option) |

### Tips

- Options should be **mutually exclusive**: one ticket should fit one option.
- Add a catch-all option like `"other"`. Otherwise Jev is forced to pick a wrong option for
  inputs that fit nothing.
- Look at the runner-up in `probabilities`. `billing: 0.55, technical: 0.45` is a very
  different situation from `billing: 0.99`, even though `choice` is the same.

---

## 7. Question type 3 — `score` (ordered scale)

**Use it for:** "Where does this fall on an ordered scale?" Examples: urgency, severity,
sentiment from very negative to very positive, quality from poor to excellent.

### Request shape

`criteria` is an **ordered array, from lowest to highest**. Index 0 is the bottom of the scale.

```json
"urgency": {
  "type": "score",
  "instructions": "How urgently should a human respond?",
  "criteria": ["Within a month", "Within a week", "Within a day", "Within an hour"]
}
```

### Response shape

```json
"urgency": {
  "type": "score",
  "score": 2.94,
  "legend": { "0": "Within a month", "1": "Within a week", "2": "Within a day", "3": "Within an hour" },
  "probabilities": { "0": 0, "1": 0, "2": 0.06, "3": 0.94 },
  "confidence": 0.94
}
```

| Field           | Meaning                                                                    |
|-----------------|----------------------------------------------------------------------------|
| `score`         | **Probability-weighted position**: Σ (index × probability). Can be fractional |
| `probabilities` | Probability for each level, keyed by index as a string                     |
| `legend`        | Maps each index back to your criteria text                                 |
| `confidence`    | How concentrated the distribution is                                       |

Check the `score` above: `0×0 + 1×0 + 2×0.06 + 3×0.94 = 2.94`. That is very close to
level 3, *"Within an hour"*, which makes sense because the customer has a demo tomorrow.

### `score` vs. `choice`

The difference is **order**. With `choice`, "billing" is not "more" than "technical". With
`score`, "within an hour" really is more urgent than "within a day". A fractional `score`
like 2.5 is meaningful ("between a day and an hour"), and you can compare scores with `>=`.

> Watch out for a split distribution: `{0: 0.5, 3: 0.5}` gives `score: 1.5`, which looks like
> "within a week", but Jev actually thinks it is *either* trivial *or* critical. Use
> `probabilities` and `confidence` to catch this.

---

## 8. Asking several questions at once

You can (and should) put **every independent question about the same state into one request**:

- They are evaluated **in parallel and independently**. One question cannot see another's
  answer, so don't write *"if the previous answer was billing, then…"*.
- The state is sent and billed once, not once per question.

If one decision really depends on another, make two requests and branch in your code between
them.

---

## 9. The raw HTTP API

```bash
curl https://openrouter.ai/api/alpha/decisions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "typesafe/jev-1.14",
    "state": { "ticket": "I was charged twice this month. Please fix this ASAP." },
    "questions": {
      "is_refund_request": {
        "type": "noul",
        "instructions": "Is the customer asking for money back?",
        "criteria": {
          "true":  "The customer requests a refund or reversal of a charge.",
          "false": "The customer does not ask for money to be returned."
        }
      },
      "urgency": {
        "type": "score",
        "instructions": "How urgently should a human respond?",
        "criteria": ["Within a month", "Within a week", "Within a day", "Within an hour"]
      }
    }
  }'
```

### Full response (real output, `jev-1.13`, three questions)

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "is_refund_request": { "type": "noul", "noul": 0.56 },
    "category": {
      "type": "choice", "choice": "billing",
      "probabilities": { "billing": 1, "technical": 0, "account": 0, "other": 0 },
      "confidence": 1
    },
    "urgency": {
      "type": "score", "score": 2.94,
      "legend": { "0": "Within a month", "1": "Within a week", "2": "Within a day", "3": "Within an hour" },
      "probabilities": { "0": 0, "1": 0, "2": 0.06, "3": 0.94 },
      "confidence": 0.94
    }
  },
  "usage": { "input_tokens": 512, "output_tokens": 79, "cost": 2.1504e-05 },
  "id": "gen-dec-1792998437-tsuWA0bfiuqpMMbTyGfj",
  "provider": "TypeSafe"
}
```

That is three decisions for **$0.0000215**.

### Request fields

| Field        | Required | Description                                                       |
|--------------|----------|-------------------------------------------------------------------|
| `model`      | yes      | e.g. `typesafe/jev-1.14`                                          |
| `state`      | yes      | String, object or array: the information to judge                 |
| `questions`  | yes      | Map of name → question definition                                 |
| `provider`   | no       | OpenRouter routing preferences (e.g. `data_collection: "deny"`)   |
| `session_id` | no       | Groups requests for observability (max 256 chars)                 |
| `user`       | no       | Your end-user identifier (max 256 chars)                          |

### Errors

Errors share one shape: `{"error": {"code": <int>, "message": <string>}}`. For example, a
`noul` question missing its `false` criterion returns `400` with a validation message that
points to the path `questions.q.criteria.false`. Other codes: `401` (bad key), `402` (no
credits), `429` (rate limited), `5xx` (upstream problems; retry with backoff).

---

## 10. Turning probabilities into actions (thresholds)

Jev hands you probabilities, and **you** decide what to do with them. Some rules:

1. **Pick thresholds from the cost of each mistake, not from round numbers.**
   Blocking a legitimate payment is expensive, so require `noul >= 0.97` to block. Sending a
   ticket to a human is cheap, so send anything above `0.4`.
2. **Use bands, not a single cutoff.** Auto-accept / human review / auto-reject.
3. **`confidence` is not a safety signal.** It only says how concentrated the distribution is.
   A model can be confidently wrong on inputs unlike anything it has seen.
4. **Tune on labelled data.** Run your questions over 20–100 examples with known answers,
   then choose cutoffs that give acceptable precision and recall.
5. **Pin the model version** when thresholds matter. `~typesafe/jev-latest` can change under
   you; `typesafe/jev-1.14` stays fixed. Re-tune when you upgrade.

### Measuring calibration (a preview of the roadmap)

Group predictions into buckets (0.0–0.1, 0.1–0.2, …). For each bucket, compare the **average
predicted probability** with the **actual fraction that were true**. A calibrated model has
those two numbers close together in every bucket. The single-number summary is the
**Expected Calibration Error (ECE)**: the weighted average gap across buckets.

---

## 11. When to use Jev — and when not to

### Good fits

| Pattern                  | Example                                                           |
|--------------------------|-------------------------------------------------------------------|
| **Routing / branching**  | Send a ticket to billing, technical or account                    |
| **Guardrails**           | Does this message contain PII, secrets or abusive language?       |
| **Tool-call approval**   | Does this proposed `DELETE FROM users` need human review?         |
| **LLM-as-judge, cheaper**| Did the agent's reply promise a discount it is not allowed to give? |
| **Triage / scoring**     | Lead quality, urgency, severity                                   |

### Poor fits

- **Multi-step reasoning or maths.** Jev makes one judgment, it does not reason through steps.
- **Precise numbers.** "Is the invoice total over $10,432.17?" Compute that in code.
- **Missing context.** A test that triaged GitHub issues by priority using only their title
  and body matched the expected labels about 10 times out of 78, because real priority
  depended on context outside the text.
- **You need an explanation.** Jev gives none; use a chat LLM for that step.

### The hybrid pattern

```
 agent / LLM / your code           Jev                     your code
 gathers the evidence     ──▶   makes the decision   ──▶   acts on probability
 (search, tools, DB)            (cheap, calibrated)        (thresholds)
```

---

## 12. Writing good instructions and criteria

1. **Describe the boundary between options.** *"Checkout, billing or payment failures"* vs.
   *"Rendering, layout or browser issues"* is much better than `billing` vs. `technical`
   with no descriptions.
2. **Make both sides of a `noul` concrete.** The `false` criterion matters as much as the
   `true` one.
3. **Order `score` criteria from lowest to highest** and make neighbouring levels distinct.
4. **Keep the state relevant.** Irrelevant context is a documented source of errors, so send
   the ticket, not the whole CRM record.
5. **Use structured state** (`{"ticket": ..., "customer_plan": ...}`) when you have several
   pieces of context. Named fields help Jev tell them apart.
6. **One question = one decision.** Don't ask *"Is it spam or urgent?"*; ask two questions.

---

## 13. Project setup

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # then put your OpenRouter key in .env
uv sync                     # install dependencies
uv run jev                  # start the API with auto-reload
```

Open **http://127.0.0.1:8000/docs**. Every endpoint can be tried from the browser there, and
each question type has its own section (tag).

`.env` variables:

| Variable              | Purpose                                   | Default                          |
|-----------------------|-------------------------------------------|----------------------------------|
| `OPENROUTER_API_KEY`  | Your OpenRouter key (keep it server-side) | none, required                   |
| `JEV_MODEL`           | Model ID to call                          | `typesafe/jev-1.14`              |
| `OPENROUTER_BASE_URL` | Decisions API base URL                    | `https://openrouter.ai/api/alpha` |
| `HOST` / `PORT`       | Where `uv run jev` serves the API         | `127.0.0.1` / `8000`             |

`.env` is git-ignored. Never commit real keys.

---

## 14. Code layout and endpoints

```
src/jev/
├── __init__.py            # main(): `uv run jev` starts uvicorn
└── app/
    ├── config.py          # global settings, loaded once from .env
    ├── client.py          # ask_jev(): the one function that calls POST /decisions
    ├── main.py            # the FastAPI app; mounts each module under its own tag
    ├── noul/              # yes / no
    │   ├── schemas.py     #   request + result models (incl. yes/review/no bands)
    │   ├── use_cases.py   #   ready-made questions: refund, PII, tool approval
    │   └── router.py      #   endpoints
    ├── choice/            # pick one option
    │   ├── schemas.py     #   request + result models (incl. runner-up and margin)
    │   ├── use_cases.py   #   ready-made questions: ticket team, intent
    │   └── router.py
    └── score/             # ordered scale
        ├── schemas.py     #   request + result models (incl. nearest level and split check)
        ├── use_cases.py   #   ready-made questions: urgency, sentiment, answer quality
        └── router.py
```

Every module follows the same three steps: **build** the question (`schemas.py` /
`use_cases.py`), **send** it with `ask_jev()`, and **interpret** the raw answer into something
your code can act on (`router.py`).

| Tag    | Endpoint                     | Input                  | What it teaches                                   |
|--------|------------------------------|------------------------|---------------------------------------------------|
| noul   | `POST /noul/ask`             | JSON body              | Any yes/no question; yes / review / no bands      |
| noul   | `GET /noul/refund-request`   | `text`, `yes_at`, `no_below` | Implied vs. explicit requests → `review` vs. `yes` |
| noul   | `GET /noul/contains-pii`     | `text`, `yes_at`, `no_below` | Guardrail with stricter bands (a leak costs more) |
| noul   | `POST /noul/tool-approval`   | JSON `{tool, arguments}` | Structured JSON as state                        |
| choice | `POST /choice/ask`           | JSON body              | Any options map; runner-up and margin             |
| choice | `GET /choice/ticket-team`    | `text`, `min_margin`   | Mixed tickets show a smaller margin               |
| choice | `GET /choice/intent`         | `text`, `min_margin`   | Workflow branching                                |
| score  | `POST /score/ask`            | JSON body              | Any ordered scale                                 |
| score  | `GET /score/urgency`         | `text`                 | Weighted score vs. nearest level                  |
| score  | `GET /score/sentiment`       | `text`                 | Mixed reviews spread over neighbouring levels     |
| score  | `POST /score/answer-quality` | JSON `{question, answer}` | Cheap LLM-as-judge                             |
| system | `GET /health`                | none                   | Shows the configured model                        |

### Real results from these endpoints (`jev-1.14`)

| Request                                                             | Result                                                     |
|---------------------------------------------------------------------|------------------------------------------------------------|
| refund-request: *"I was charged twice… Please fix this ASAP."*       | `0.40` → **review** (refund only implied)                  |
| refund-request: *"Please refund the duplicate charge on my card."*   | `0.99` → **yes**                                           |
| tool-approval: `sql.execute` with `DELETE FROM users …`             | `0.96` → **yes**, needs a human                            |
| ticket-team: *"blank page after login, and I am also double billed"* | technical `0.64`, billing `0.29`: two problems in one ticket |
| sentiment: *"Setup was painful, but support was great…"*             | score `2.79`: Neutral `0.21`, Positive `0.79`              |
| answer-quality: *"Sydney is the capital of Australia"*               | score `0.26` → **wrong** (it is Canberra)                  |

Each call cost about **$0.000015**.

### Next steps

- [ ] **Multi-question:** `POST /decide` with any mix of types in one request (README §8)
- [ ] **Evaluation:** run a small labelled dataset and measure accuracy and calibration (ECE, §10)

---

### Sources

- [Jev on OpenRouter](https://openrouter.ai/docs/guides/community/jev)
- [Jev tutorial](https://openrouter.ai/docs/guides/community/jev-tutorial.md)
- [Decisions API reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-questions-and-answers-request.md)
- [What is Jev and when to use it (Mastra)](https://mastra.ai/articles/jev)
