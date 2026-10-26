def main() -> None:
    """Entry point for `uv run jev`: serve the FastAPI app with auto-reload."""
    import uvicorn

    from jev.app.config import settings

    uvicorn.run("jev.app.main:app", host=settings.host, port=settings.port, reload=True)
