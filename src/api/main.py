import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router as queries_router
from src.api.database import init_db

def create_app() -> FastAPI:
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

    @app.on_event("startup")
    def on_startup():
        init_db()

    app.include_router(queries_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "service": "AWIS DeepAgent Backend"}

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)