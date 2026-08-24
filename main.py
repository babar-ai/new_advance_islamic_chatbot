from services.openai_service import OpenAIService
from utils.custom_logger import setup_logger



logger = setup_logger(__name__)
openai_service = OpenAIService()

while True:
    query = input("Enter your query: ")

    try:
        query_embedding = openai_service.embed_query(query)
        # logger.info(f"Query embedding: {query_embedding}")

    except Exception as e:
        logger.error(f"Error embedding query: {e}")

    try:
        result = openai_service.classify_query(query, query_embedding)

        logger.info(f"Classification result: {result}")

    except Exception as e:
        logger.error(f"Error classifying query: {e}")