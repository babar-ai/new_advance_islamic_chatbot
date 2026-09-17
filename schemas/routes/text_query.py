
from typing import Optional
from pydantic import BaseModel, Field


class TextQuerySchema(BaseModel):
    """Request schema for the /text_query and /text_query/stream endpoints."""

    query: str = Field(
        ...,
        min_length=1,
        description="The user's Islamic question or query"
    )

    session_id: Optional[str] = Field(
        default=None,
        description=(
            "UUID identifying the conversation session. "
            "Send the value returned from the previous response to continue a conversation. "
            "Omit (or send null) to start a new session — a fresh UUID will be generated and returned."
        )
    )
