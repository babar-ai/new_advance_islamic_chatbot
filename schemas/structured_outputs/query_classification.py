
from typing import Literal, List, Optional

from pydantic import BaseModel, Field


class MetadataFilterSchema(BaseModel):

    surah_number: Optional[int] = Field(
        default=None,
        description="Surah number if specifically mentioned (e.g., 2 for Surah Al-Baqarah, 1 for Al-Fatiha, 112 for Al-Ikhlas)."
    )

    ayah_number: Optional[int] = Field(
        default=None,
        description="Ayah/verse number if specifically mentioned (e.g., 255 for Ayatul Kursi, 153 for 2:153)."
    )

    hadith_book: Optional[str] = Field(
        default=None,
        description="Name of specific Hadith book if mentioned (e.g., 'Sahih al-Bukhari', 'Sahih Muslim', 'Sunan Abi Dawud', 'Jami` at-Tirmidhi')."
    )
    


class QueryClassificationSchema(BaseModel):

    """Structured output for query classification"""


    required_sources: List[Literal['quran', 'hadith', 'tafseer', 'general_islamic_info']] = Field(
        description="List of required sources from: quran, hadith, tafseer"
    ) 


    reasoning: str = Field(
        description="Brief explanation of why these sources were selected"
    )


    filters: Optional[MetadataFilterSchema] = Field(
        default=None,
        description="Optional metadata filters if the query specifies a particular Surah number, Ayah number, or Hadith book."
    )

