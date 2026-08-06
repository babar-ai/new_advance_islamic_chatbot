"""
Document Loading and Splitting Module for Islamic AI Chatbot.
"""

import sys
from pathlib import Path
from typing import Iterator, List, Optional

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.custom_logger import setup_logger
from utils.config import settings

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import json 


if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = setup_logger(__name__)


class IslamicJSONLoader(BaseLoader):
    """LangChain-compatible loader for Islamic JSON datasets."""

    CONTENT_KEY_PRIORITY = ["translation", "tafsir", "text", "content", "body"]

    def __init__(self, file_path: str, content_key: Optional[str] = None):
        self.file_path = Path(file_path)
        self.content_key = content_key

    def lazy_load(self) -> Iterator[Document]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            return

        for idx, record in enumerate(data):
            if not isinstance(record, dict):
                record = {"text": str(record)}

            content_key = self.content_key
            if not content_key:
                for candidate in self.CONTENT_KEY_PRIORITY:
                    if candidate in record:
                        content_key = candidate
                        break

            if not content_key and record:
                content_key = next(iter(record))
                
            if "narrator" in record and "translation" in record:
                page_content = f"{record['narrator']}\n{record['translation']}".strip()
                skip_metadata_keys = {"translation", "narrator"}
            else:
                page_content = str(record.get(content_key, "")).strip()
                skip_metadata_keys = {content_key}

            if not page_content:
                continue

            metadata: dict = {}

            if "narrator" in record and isinstance(record["narrator"], (str, int, float, bool)):
                metadata["narrator"] = record["narrator"]

            for key, value in record.items():
                if key in skip_metadata_keys:
                    continue

                if isinstance(value, dict):
                    for sub_key, sub_val in value.items():
                        if not isinstance(sub_val, (dict, list)):
                            metadata[sub_key] = sub_val
                elif not isinstance(value, list):
                    metadata[key] = value

            yield Document(page_content=page_content, metadata=metadata)


def preprocess_docs(folder_path: str) -> List[Document]:
    """Recursively scans folder_path (.txt and .json) and loads Documents."""
    folder = Path(folder_path)
    documents: List[Document] = []

    if not folder.exists() or not folder.is_dir():
        logger.warning("Folder not found, skipping: %s", folder_path)
        return documents

    logger.info("Scanning: %s", folder.resolve())

    txt_loader = DirectoryLoader(
        path=str(folder),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
        use_multithreading=False,
        silent_errors=True,
    )

    txt_docs = txt_loader.load()

    for doc in txt_docs:
        file_path = Path(doc.metadata.get("source", ""))
        doc.metadata["book_name"] = file_path.stem.replace("_", " ").title()

    if txt_docs:
        logger.info(".txt files -> %d document(s) loaded", len(txt_docs))

    documents.extend(txt_docs)

    json_files = list(folder.rglob("*.json"))

    for json_file in json_files:
        logger.info("Loading JSON: %s", json_file.relative_to(folder))

        try:
            loader = IslamicJSONLoader(str(json_file))
            loaded = loader.load()
            logger.info("  -> %d record(s) loaded", len(loaded))
            documents.extend(loaded)
            
        except Exception as exc:
            logger.error("Failed to load '%s': %s", json_file.name, exc)

    logger.info("Total documents from '%s': %d", folder.name, len(documents))
    return documents



def split_documents(documents: List[Document]) -> List[Document]:
    """Splits a list of Documents into smaller chunks."""
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    return splitter.split_documents(documents)

