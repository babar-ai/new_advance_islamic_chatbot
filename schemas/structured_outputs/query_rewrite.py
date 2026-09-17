from pydantic import BaseModel, Field


class QueryRewriteSchema(BaseModel):
    """Structured output for query rewriting"""

    standalone_query: str = Field(
        description="The reformulated standalone search question for Islamic knowledge retrieval. Combines the follow-up intent with context from prior turns. NEVER answer the question."
    )
