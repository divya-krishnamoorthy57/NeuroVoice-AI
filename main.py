import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import init_db, engine
from config import FRONTEND_ORIGINS
from routers import (
    auth, profile, exercises, practice, dashboard,
    progress, preferences, plans, contact, admin
)
from routes import speech  # Legacy route preserved

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neurovoice.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: safely verify and migrate DB tables without data loss
    logger.info("Initializing NeuroVoice AI database...")
    try:
        init_db()
        logger.info("Database initialized and verified successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    yield
    # Shutdown
    logger.info("NeuroVoice AI backend shutting down.")


app = FastAPI(
    title="NeuroVoice AI API",
    description="Backend API for NeuroVoice AI — Empowering Communication Through Practice.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS + [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Checks
@app.get("/", tags=["Health"])
def home():
    return {
        "status": "healthy",
        "app": "NeuroVoice AI API",
        "tagline": "Empowering Communication Through Practice",
        "version": "2.0.0"
    }


@app.get("/health", tags=["Health"])
def health_check():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "2.0.0"
    }


# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(exercises.router, prefix="/exercises", tags=["Exercises"])
app.include_router(practice.router, prefix="/practice", tags=["Practice"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(progress.router, prefix="/progress", tags=["Progress"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
app.include_router(plans.router, prefix="/plans", tags=["Practice Plans"])
app.include_router(contact.router, prefix="/contact", tags=["Contact"])
app.include_router(admin.router, prefix="/admin", tags=["Administration"])

# Legacy Route for backward compatibility
app.include_router(speech.router, prefix="/speech", tags=["Legacy Speech"])