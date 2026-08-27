
import logging
import os

from fastapi import FastAPI, HTTPException

from schemas.routes.text_query import TextQuerySchema
from services.langgraph_service import LangGraphService
from utils.config import settings
from utils.custom_logger import setup_logger

logger = setup_logger(__name__)

# ── LangSmith Tracing Setup ───────────────────────────────────────────────────
# LangGraph traces all nodes automatically when these env vars are set.
if settings.langsmith_enabled:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    logger.info("LangSmith tracing ENABLED → project: '%s'", settings.LANGCHAIN_PROJECT)
else:
    logger.info("LangSmith tracing DISABLED (set LANGCHAIN_API_KEY in .env to enable)")

# ── App Setup ─────────────────────────────────────────────────────────────────
application = FastAPI(
    title="Islamic Knowledge Chatbot API",
    description="An AI-powered chatbot answering Islamic questions using Quran, Hadith, Tafsir, and General Islamic sources.",
    version=settings.VERSION,
)

# ── Service Initialization ─────────────────────────────────────────────────────
langgraph_service = LangGraphService()

# ── Routes ─────────────────────────────────────────────────────────────────────

@application.get("/")
async def health_check():
    """Health check — returns API version."""
    return {"status": "ok", "version": settings.VERSION}


@application.post("/text_query")
async def process_text_query(request: TextQuerySchema):
    """
    Process a user's Islamic text query through the full LangGraph pipeline:
        classify_and_search → parallel_retrieve → generate_response
    """
    user_input = request.query.strip()
    logger.info("Received text query: %s", user_input[:80])

    try:
        llm_response = langgraph_service.query(user_input)

        if not llm_response:
            logger.error("LLM returned an empty response.")
            raise HTTPException(status_code=500, detail="Failed to generate a response.")

        return {
            "status": "success",
            "query": user_input,
            "message": llm_response,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Unexpected error in /text_query: %s", e)
        return {
            "status": "error",
            "message": f"Error processing query: {str(e)}",
        }
