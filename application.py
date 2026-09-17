import asyncio
import json
import logging
import os
import uuid

import redis.asyncio as redis

from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from schemas.routes.text_query import TextQuerySchema
from services.langgraph_service import LangGraphService
from services.qdrant_service import QdrantService
from services.openai_service import OpenAIService

from utils.config import settings
from utils.custom_logger import setup_logger

from fastapi.middleware.cors import CORSMiddleware

logger = setup_logger(__name__)


# ─────────────────────────────────────────────
# LangSmith
# ─────────────────────────────────────────────

if settings.langsmith_enabled:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

    logger.info(
        "LangSmith tracing ENABLED → project: '%s'",
        settings.LANGCHAIN_PROJECT
    )


# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting application...")

    # Thread pools
    classification_executor = ThreadPoolExecutor(
        max_workers=4
    )

    retrival_executor = ThreadPoolExecutor(
        max_workers=8
    )

    app.state.classification_executor = classification_executor
    app.state.retrival_executor = retrival_executor

    # ─────────────────────────────────────────────
    # Services
    # ─────────────────────────────────────────────

    qdrant_service = QdrantService()

    openai_service = OpenAIService(
        qdrant_service=qdrant_service
    )

    langgraph_service = LangGraphService(
        qdrant_service=qdrant_service,
        openai_service=openai_service,
        classification_executor=app.state.classification_executor,
        retrival_executor=app.state.retrival_executor,
    )

    # Build and compile the LangGraph with the Redis checkpointer.
    # This must be awaited here (in async lifespan) because AsyncRedisSaver
    # requires an async context to open its Redis connection.
    await langgraph_service.setup_graph()

    app.state.langgraph_service = langgraph_service

    # Redis
    redis_connection = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    # Initialize rate limiter
    await FastAPILimiter.init(redis_connection)

    logger.info("Redis rate limiter initialized")

    try:
        yield

    finally:

        logger.info("Shutting down application...")

        classification_executor.shutdown()
        retrival_executor.shutdown()

        # Cleanly close the Redis checkpointer connection
        await langgraph_service.teardown_graph()

        await redis_connection.close()

        logger.info("Application shutdown complete")


# ─────────────────────────────────────────────
# FastAPI
# ─────────────────────────────────────────────

application = FastAPI(
    title="Islamic Knowledge Chatbot API",
    description=(
        "An AI-powered chatbot answering Islamic questions "
        "using Quran, Hadith, Tafsir, and General Islamic sources."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)


application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@application.get("/")                          # a GET request is an HTTP request used mainly to retrieve/read data from a server.
async def health_check():

    return {
        "status": "ok",
        "version": settings.VERSION,
    }


# ─────────────────────────────────────────────
# RAG endpoint (synchronous / bulk response)
# ─────────────────────────────────────────────

@application.post(                             # POST is used when the client sends data/instructions to the server and the request causes some processing or state change.
    "/text_query",
    dependencies=[
        Depends(
            RateLimiter(
                times=10,
                seconds=60
            )
        )
    ]
)


async def process_text_query(
    request: Request,
    query_request: TextQuerySchema,
):
    user_input = query_request.query.strip()

    # session_id identifies the conversation thread for the checkpointer.
    # If the client doesn't send one (e.g. first message), generate a new UUID.
    session_id = query_request.session_id or str(uuid.uuid4())

    langgraph_service = request.app.state.langgraph_service

    logger.info(
        "Received text query: session_id=%s query=%s",
        session_id, user_input[:80]
    )

    try:

        async with asyncio.timeout(120):

            llm_response = await langgraph_service.aquery(user_input, session_id=session_id)

            if not llm_response:

                logger.error("LLM returned an empty response.")

                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate a response."
                )

            return {
                "status": "success",
                "query": user_input,
                "message": llm_response,
                "session_id": session_id,   # Return to client so they can persist it
            }

    except TimeoutError:

        logger.exception("Request timeout")

        raise HTTPException(
            status_code=504,
            detail="Request took too long to process."
        )

    except HTTPException:
        raise

    except Exception:

        logger.exception("Unexpected RAG failure")

        raise HTTPException(
            status_code=500,
            detail="Unable to process your request right now."
        )


# ─────────────────────────────────────────────
# RAG endpoint (streaming / Server-Sent Events)
# ─────────────────────────────────────────────

@application.post(
    "/text_query/stream",
    dependencies=[
        Depends(
            RateLimiter(
                times=10,
                seconds=60
            )
        )
    ]
)
async def stream_text_query(
    request: Request,
    query_request: TextQuerySchema,
):
    """
    Streaming endpoint that returns Server-Sent Events (SSE).
    Each event is a JSON object with one of these shapes:
        {"status": "searching"|"generating", "message": "..."}   — progress update
        {"token": "...", "done": false}                          — LLM token chunk
        {"done": true, "full_response": "...", "session_id": "..."} — final complete text
    """

    user_input = query_request.query.strip()
    session_id = query_request.session_id or str(uuid.uuid4())
    langgraph_service = request.app.state.langgraph_service

    logger.info(
        "[STREAM] session_id=%s query=%s",
        session_id, user_input[:80]
    )

    async def event_generator():
        try:
            async for event in langgraph_service.query_stream(user_input, session_id=session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Streaming error")
            error_event = {"done": True, "full_response": f"I apologize, but I encountered an error: {str(e)}", "session_id": session_id}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )