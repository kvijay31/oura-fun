"""Start the FastAPI dev server for local development.

    uv run python scripts/run_api.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "oura_fun.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
