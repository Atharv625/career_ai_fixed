"""
Career Advisor Chatbot - Gemini AI + TF-IDF RAG
Lazy-initialized singleton: never blocks at import time.
"""

import os
import json
import time
import asyncio
import logging
import pathlib
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURATION  (read at import time – no heavy work yet)
# ═══════════════════════════════════════════════════════════

DATA_DIR              = pathlib.Path(os.getenv("DATA_DIR", "data"))
MAX_SESSIONS          = int(os.getenv("MAX_SESSIONS",          500))
MAX_MESSAGE_LENGTH    = int(os.getenv("MAX_MESSAGE_LENGTH",   2000))
MIN_MESSAGE_LENGTH    = int(os.getenv("MIN_MESSAGE_LENGTH",      3))
SIMILARITY_THRESHOLD  = float(os.getenv("SIMILARITY_THRESHOLD", 0.1))
MAX_RETRIES           = int(os.getenv("MAX_RETRIES",             3))
RETRY_DELAY           = float(os.getenv("RETRY_DELAY",         1.0))
RATE_LIMIT_REQUESTS   = int(os.getenv("RATE_LIMIT_REQUESTS",    10))
RATE_LIMIT_WINDOW     = int(os.getenv("RATE_LIMIT_WINDOW",      60))
GEMINI_TIMEOUT        = int(os.getenv("GEMINI_TIMEOUT",         45))
GEMINI_MODEL          = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ═══════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests  = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        self.requests.setdefault(user_id, [])
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if now - ts < self.window_seconds
        ]
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True


# ═══════════════════════════════════════════════════════════
# INPUT VALIDATION
# ═══════════════════════════════════════════════════════════

def validate_message(message: str):
    if not message or not isinstance(message, str):
        return False, "Message cannot be empty."
    message = message.strip()
    if len(message) < MIN_MESSAGE_LENGTH:
        return False, f"Message too short (min {MIN_MESSAGE_LENGTH} chars)."
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {MAX_MESSAGE_LENGTH} chars)."
    return True, None


# ═══════════════════════════════════════════════════════════
# LRU SESSION CACHE
# ═══════════════════════════════════════════════════════════

class LRUSessionCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                evicted, _ = self.cache.popitem(last=False)
                logger.warning(f"LRU eviction: removed session {evicted}")
        self.cache[key] = value

    def remove(self, key: str):
        self.cache.pop(key, None)


# ═══════════════════════════════════════════════════════════
# KNOWLEDGE BASE  (heavy – built lazily inside the singleton)
# ═══════════════════════════════════════════════════════════

class CareerKnowledgeBase:
    def __init__(self):
        # Deferred imports so they don't block FastAPI startup
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        self._cosine_similarity = cosine_similarity
        self.documents: List[str] = []
        self.doc_metadata: List[Dict] = []
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9,
            sublinear_tf=True,
        )
        self.tfidf_matrix = None
        self._load_and_index()

    def _load_and_index(self):
        careers_path = DATA_DIR / "careers.json"
        courses_path = DATA_DIR / "courses.json"

        if not careers_path.exists():
            logger.warning(f"careers.json not found at {careers_path}; KB will be empty")
            careers = []
        else:
            careers = json.loads(careers_path.read_text())

        if not courses_path.exists():
            logger.warning(f"courses.json not found at {courses_path}; KB will be empty")
            courses = []
        else:
            courses = json.loads(courses_path.read_text())

        for idx, career in enumerate(careers):
            try:
                text = (
                    f"{career['career_name']} {career['description']} "
                    f"skills: {' '.join(career.get('required_skills', []))} "
                    f"tags: {' '.join(career.get('tags', []))}"
                )
                self.documents.append(text)
                self.doc_metadata.append({"type": "career", "data": career})
            except KeyError as e:
                logger.warning(f"Skipping malformed career {idx}: {e}")

        for idx, course in enumerate(courses):
            try:
                text = (
                    f"{course['course_name']} {course.get('platform', '')} "
                    f"teaches: {' '.join(course.get('skills_taught', []))} "
                    f"for: {' '.join(course.get('career_category', []))}"
                )
                self.documents.append(text)
                self.doc_metadata.append({"type": "course", "data": course})
            except KeyError as e:
                logger.warning(f"Skipping malformed course {idx}: {e}")

        if self.documents:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
            logger.info(
                f"✅ KB indexed: {len(careers)} careers, "
                f"{len(courses)} courses ({len(self.documents)} docs)"
            )
        else:
            logger.warning("Knowledge base is empty – no documents indexed")

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        if not query.strip() or self.tfidf_matrix is None:
            return []
        try:
            q_vec = self.vectorizer.transform([query])
            sims  = self._cosine_similarity(q_vec, self.tfidf_matrix).flatten()
            top_i = sims.argsort()[-top_k:][::-1]
            return [self.doc_metadata[i] for i in top_i if sims[i] > SIMILARITY_THRESHOLD]
        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            return []


# ═══════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are CareerPath AI, a friendly and expert career advisor for students and professionals.

Your role is to:
1. Help users choose the right career path based on their interests, skills, and goals
2. Provide detailed skill gap analyses
3. Generate structured learning roadmaps
4. Recommend specific courses and certifications
5. Give placement and interview preparation guidance

RESPONSE GUIDELINES:
- Structure responses clearly with headers and bullet points
- Be encouraging, specific, and actionable
- Include salary ranges and job market outlook when relevant
- Keep responses concise but comprehensive (300-500 words unless asked for detail)
- Use emojis sparingly (🎯 📚 💡)

IMPORTANT: You have access to retrieved context from a knowledge base. Prioritize this context
for specific recommendations. If context doesn't cover something, use your general knowledge."""


# ═══════════════════════════════════════════════════════════
# MAIN CHATBOT CLASS
# ═══════════════════════════════════════════════════════════

class CareerAdvisorChatbot:
    def __init__(self):
        # Validate API key at construction time (not at import time)
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to .env or docker-compose environment."
            )

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai

        self.knowledge_base  = CareerKnowledgeBase()
        self.session_cache   = LRUSessionCache(max_size=MAX_SESSIONS)
        self.rate_limiter    = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
        self.metrics = {
            "total_messages": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "rate_limited": 0,
            "timeout_errors": 0,
        }
        logger.info(f"🤖 Chatbot ready. Model: {GEMINI_MODEL}")

    def _build_rag_context(self, retrieved: List[Dict]) -> str:
        if not retrieved:
            return ""
        parts = ["--- RETRIEVED KNOWLEDGE BASE CONTEXT ---"]
        for item in retrieved:
            try:
                if item["type"] == "career":
                    c = item["data"]
                    sal = c.get("salary_range", {})
                    parts.append(
                        f"\nCAREER: {c.get('career_name', 'Unknown')}\n"
                        f"Description: {c.get('description', 'N/A')}\n"
                        f"Required Skills: {', '.join(c.get('required_skills', []))}\n"
                        f"Salary Range: ${sal.get('min','N/A'):,} – ${sal.get('max','N/A'):,} USD\n"
                        f"Roadmap: {' → '.join(c.get('roadmap', [])[:5])}\n"
                        f"Growth Outlook: {c.get('growth_outlook', 'N/A')}"
                    )
                elif item["type"] == "course":
                    c = item["data"]
                    parts.append(
                        f"\nCOURSE: {c.get('course_name', 'Unknown')}\n"
                        f"Platform: {c.get('platform','N/A')} | Rating: {c.get('rating','N/A')}/5\n"
                        f"Duration: {c.get('duration','N/A')} | Price: {c.get('price','N/A')}\n"
                        f"Skills Taught: {', '.join(c.get('skills_taught', []))}"
                    )
            except Exception as e:
                logger.warning(f"Context build error: {e}")
        parts.append("--- END CONTEXT ---")
        return "\n".join(parts)

    def _extract_reply(self, response) -> str:
        try:
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            pass
        try:
            return response.candidates[0].content.parts[0].text
        except Exception:
            pass
        return (
            "I'm sorry, I couldn't generate a response. "
            "Please try rephrasing your question or try again later."
        )

    async def _send_with_retry(
        self, user_id: str, prompt: str, attempt: int = 0
    ):
        try:
            def _call():
                model = self._genai.GenerativeModel(GEMINI_MODEL)
                return model.generate_content(prompt)

            loop = asyncio.get_running_loop()
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, _call),
                    timeout=GEMINI_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Gemini timeout after {GEMINI_TIMEOUT}s")

            return self._extract_reply(response), True

        except (ConnectionError, TimeoutError) as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Retry {attempt+1}/{MAX_RETRIES} for {user_id}: {e} (wait {wait}s)")
                await asyncio.sleep(wait)
                return await self._send_with_retry(user_id, prompt, attempt + 1)
            self.metrics["timeout_errors"] += 1
            logger.error(f"Max retries exceeded for {user_id}: {e}")
            return None, False

        except Exception as e:
            logger.error(f"Gemini error for {user_id}: {e}", exc_info=True)
            return None, False

    async def chat(
        self,
        user_id: str,
        message: str,
        student_profile: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        self.metrics["total_messages"] += 1

        is_valid, error_msg = validate_message(message)
        if not is_valid:
            return {"response": error_msg, "sources": [], "has_context": False, "success": False}

        if not self.rate_limiter.is_allowed(user_id):
            self.metrics["rate_limited"] += 1
            return {
                "response": (
                    f"Too many requests. Please wait before sending another message. "
                    f"(Limit: {RATE_LIMIT_REQUESTS} per {RATE_LIMIT_WINDOW}s)"
                ),
                "sources": [], "has_context": False, "success": False,
            }

        retrieved    = self.knowledge_base.retrieve(message.strip(), top_k=3)
        rag_context  = self._build_rag_context(retrieved)

        profile_context = ""
        if student_profile:
            try:
                profile_context = (
                    f"\n--- STUDENT PROFILE ---\n"
                    f"Name: {student_profile.get('name', 'Student')}\n"
                    f"Education: {student_profile.get('education', 'Not specified')}\n"
                    f"Current Skills: {', '.join(student_profile.get('skills', []))}\n"
                    f"Interests: {', '.join(student_profile.get('interests', []))}\n"
                    f"Career Goal: {student_profile.get('career_goal', 'Not specified')}\n"
                    f"--- END PROFILE ---"
                )
            except Exception as e:
                logger.warning(f"Profile context error: {e}")

        prompt = f"{SYSTEM_PROMPT}\n\n{rag_context}\n\n{profile_context}\n\nUser Question: {message}"

        reply, success = await self._send_with_retry(user_id, prompt)

        if success:
            self.metrics["successful_responses"] += 1
        else:
            self.metrics["failed_responses"] += 1
            reply = "I'm experiencing a technical issue right now. Please try again in a moment."

        sources = [
            item["data"].get("career_name") or item["data"].get("course_name", "Unknown")
            for item in retrieved
        ]

        return {"response": reply, "sources": sources, "has_context": bool(retrieved), "success": success}

    def clear_session(self, user_id: str):
        self.session_cache.remove(user_id)
        logger.info(f"Cleared session for {user_id}")

    def get_metrics(self) -> Dict[str, Any]:
        return {**self.metrics, "active_sessions": len(self.session_cache.cache), "ts": time.time()}


# ═══════════════════════════════════════════════════════════
# LAZY SINGLETON  – import this function, never the module-level object
# ═══════════════════════════════════════════════════════════

_chatbot_instance: Optional[CareerAdvisorChatbot] = None


def get_chatbot() -> CareerAdvisorChatbot:
    """Return the singleton chatbot, creating it on first call."""
    global _chatbot_instance
    if _chatbot_instance is None:
        logger.info("Initialising CareerAdvisorChatbot…")
        _chatbot_instance = CareerAdvisorChatbot()
    return _chatbot_instance
