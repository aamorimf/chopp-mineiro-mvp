from fastapi import FastAPI

app = FastAPI(
    title="Boteco do Mineiro MVP",
    version="0.1.0",
)


@app.get("/")
def health_check() -> dict[str, str]:
    """Return a basic health check for the API."""
    return {"status": "ok", "message": "Boteco do Mineiro API is running"}