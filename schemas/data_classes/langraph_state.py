
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class LangGraphState:
    """State object that flows through the LangGraph pipeline."""
    user_query: str
    query_embedding: Optional[List[float]] = None          # Embed once, reuse everywhere
    web_search_results: List[Dict] = field(default_factory=list)
    required_sources: List[str] = field(default_factory=list)  # ["quran", "hadith", "tafseer", "general_islamic_info"]
    classification_reasoning: str = ""
    retrieved_documents: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    final_response: str = ""
    error_message: Optional[str] = None
