"""The FastAPI application. Each question type is its own module with its own tag.

Run it with `uv run jev`, then open http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from jev.app import choice, noul, score
from jev.app.config import settings

app = FastAPI(
    title="Learning Jev",
    description="Jev decision model (TypeSafe AI) via OpenRouter: noul, choice and score questions.",
    version="0.1.0",
)

# The tag groups each module's endpoints under its own section in /docs
app.include_router(noul.router, prefix="/noul", tags=["noul (yes / no)"])
app.include_router(choice.router, prefix="/choice", tags=["choice (pick one)"])
app.include_router(score.router, prefix="/score", tags=["score (ordered scale)"])


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness check; also shows which Jev model the app is configured to call."""
    return {"status": "ok", "model": settings.jev_model}
