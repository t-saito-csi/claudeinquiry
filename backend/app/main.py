from fastapi import FastAPI

app = FastAPI(
    title="問診システム API",
    description="大規模病院向けデジタル問診システム",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
