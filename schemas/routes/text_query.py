
from pydantic import BaseModel, Field


class TextQuerySchema(BaseModel):
    """Request schema for the /text_query endpoint."""
    query: str = Field(..., min_length=1, description="The user's Islamic question or query")      #here '...' means it is required , and the '1' means the minimum length of the query should be 1 character.
