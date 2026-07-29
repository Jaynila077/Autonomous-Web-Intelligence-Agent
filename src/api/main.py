from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(title="AWIS Autonomous OSINT API", version="2.0")

app.include_router(router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "active", "system": "AWIS DeepAgents Pipeline"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)


