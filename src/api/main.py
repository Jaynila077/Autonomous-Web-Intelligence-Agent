from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.api.routes import router

app = FastAPI(title="AWIS Autonomous OSINT API", version="2.0")

app.include_router(router, prefix="/api/v1")

# Serve the console's static assets (index.html lives here)
app.mount("/static", StaticFiles(directory="src/ui/static"), name="static")

@app.get("/")
def serve_console():
    return FileResponse("src/ui/static/index.html")

@app.get("/health")
def health_check():
    return {"status": "active", "system": "AWIS DeepAgents Pipeline"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
