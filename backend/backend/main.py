from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from database import db
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DevBuddy AI",
    description="AI-powered coding workspace",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    logger.info("DevBuddy AI backend started")

@app.on_event("shutdown")
async def shutdown():
    logger.info("DevBuddy AI backend shutting down")

@app.get("/")
async def root():
    return {
        "name": "DevBuddy AI",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )