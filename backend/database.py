"""
Database Module - MongoDB async connection using Motor.
Handles connection lifecycle and collection accessors.
"""

import os
import json
import logging
import pathlib
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None


db_instance = Database()


# ─────────────────────────────────────────────────────────
# Connection Management
# ─────────────────────────────────────────────────────────

async def connect_to_mongo() -> None:
    """Establish MongoDB connection on application startup."""
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name   = os.getenv("MONGODB_DB",  "career_advisor")

    logger.info(f"Connecting to MongoDB at {mongo_url} (db: {db_name})")
    db_instance.client = AsyncIOMotorClient(
        mongo_url,
        serverSelectionTimeoutMS=5000,   # fail fast on bad URL
        connectTimeoutMS=5000,
    )
    db_instance.db = db_instance.client[db_name]

    # Verify the connection is actually usable before returning
    await db_instance.client.admin.command("ping")
    logger.info(f"✅ Connected to MongoDB: {db_name}")

    await _seed_initial_data()


async def close_mongo_connection() -> None:
    """Close MongoDB connection on application shutdown."""
    if db_instance.client:
        db_instance.client.close()
        logger.info("🔴 MongoDB connection closed")


# ─────────────────────────────────────────────────────────
# Collection Accessors
# ─────────────────────────────────────────────────────────

def get_students_collection():
    return db_instance.db["students"]

def get_careers_collection():
    return db_instance.db["careers"]

def get_courses_collection():
    return db_instance.db["courses"]

def get_chat_history_collection():
    return db_instance.db["chat_history"]


# ─────────────────────────────────────────────────────────
# Seed Initial Data
# ─────────────────────────────────────────────────────────

async def _seed_initial_data() -> None:
    """Load careers.json and courses.json into MongoDB if collections are empty."""
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    logger.info(f"Seeding from: {DATA_DIR}")

    careers_col = get_careers_collection()
    if await careers_col.count_documents({}) == 0:
        careers_file = DATA_DIR / "careers.json"
        if careers_file.exists():
            careers = json.loads(careers_file.read_text())
            await careers_col.insert_many(careers)
            logger.info(f"📚 Seeded {len(careers)} careers")
        else:
            logger.warning(f"⚠️  careers.json not found at {careers_file}")

    courses_col = get_courses_collection()
    if await courses_col.count_documents({}) == 0:
        courses_file = DATA_DIR / "courses.json"
        if courses_file.exists():
            courses = json.loads(courses_file.read_text())
            await courses_col.insert_many(courses)
            logger.info(f"🎓 Seeded {len(courses)} courses")
        else:
            logger.warning(f"⚠️  courses.json not found at {courses_file}")
