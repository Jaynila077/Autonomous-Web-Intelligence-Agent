# src/api/app.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router as queries_router

def create_app() -> FastAPI:
    """
    Application factory for the AWIS FastAPI Backend.
    """
    app = FastAPI(
        title="AWIS DeepAgent API",
        description="Autonomous Web Intelligence Agent - Asynchronous Research API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(queries_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Simple health check endpoint to confirm API operational status."""
        return {"status": "ok", "service": "AWIS DeepAgent Backend"}

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("src/api.app:app", host="0.0.0.0", port=8000, reload=True)


