# src/api/main.py
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from arq import create_pool
from arq.connections import RedisSettings

from src.api.router import router as queries_router
from src.api.auth import router as auth_router
from src.api.database import init_db

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379"))


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
    async def on_startup():
        init_db()
        # Initialize arq Redis connection pool
        app.state.arq_redis = await create_pool(RedisSettings.from_dsn(UPSTASH_REDIS_URL))

    @app.on_event("shutdown")
    async def on_shutdown():
        # Close arq Redis pool cleanly
        if hasattr(app.state, "arq_redis") and app.state.arq_redis:
            await app.state.arq_redis.close()

    # Mount routers
    app.include_router(auth_router)
    app.include_router(queries_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "service": "AWIS DeepAgent Backend"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)