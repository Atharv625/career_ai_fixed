"""
Career Advisor AI - FastAPI Backend
Main entry point with lifespan-based startup (replaces deprecated on_event).
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from database import connect_to_mongo, close_mongo_connection
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Lifespan (replaces deprecated @app.on_event)
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup → yield → shutdown."""
    logger.info("🚀 Starting Career Advisor AI backend…")
    await connect_to_mongo()

    # Lazy-initialize the chatbot AFTER the event loop is running
    # (avoids blocking import-time TF-IDF construction)
    from chatbot import get_chatbot
    get_chatbot()          # warms the singleton
    logger.info("✅ All services initialised")

    yield                  # ← application runs here

    logger.info("🔴 Shutting down…")
    await close_mongo_connection()


# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Career Advisor AI",
    description="One-Stop Career & Education Advice powered by Gemini AI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────
from routers import chat, careers, students, recommendations, roadmap, skill_gap  # noqa: E402

app.include_router(chat.router,            prefix="/api/chat",            tags=["AI Chatbot"])
app.include_router(careers.router,         prefix="/api/careers",         tags=["Careers"])
app.include_router(students.router,        prefix="/api/students",        tags=["Students"])
app.include_router(recommendations.router, prefix="/api/recommendations",  tags=["Recommendations"])
app.include_router(roadmap.router,         prefix="/api/roadmap",         tags=["Learning Roadmap"])
app.include_router(skill_gap.router,       prefix="/api/skill-gap",       tags=["Skill Gap Analysis"])

# ─────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "Career Advisor AI", "version": "1.0.0"}
