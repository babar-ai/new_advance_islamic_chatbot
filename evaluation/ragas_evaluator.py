"""
ragas_evaluator.py
------------------
Runs RAGAS reference-free metrics on a PipelineTrace captured from the
live Islamic chatbot pipeline.

Metrics used (all reference-free — no ground truth needed):
  - faithfulness       : Are all claims supported by retrieved context?
  - answer_relevancy   : Does the answer actually address the question?
  - context_precision  : How many retrieved chunks are truly useful?

The RAGAS judge LLM uses the same OpenAI key already in .env.
"""

import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.custom_logger import setup_logger
from utils.config import settings

logger = setup_logger(__name__)


def _patch_missing_vertexai() -> None:
    """
    ragas imports langchain_community.chat_models.vertexai which was removed
    in langchain-community >= 0.3. This stub satisfies the import without
    requiring the actual Google VertexAI SDK.
    """
    import sys
    import types

    # Only patch if the module is actually missing
    if "langchain_community.chat_models.vertexai" not in sys.modules:
        try:
            # Try the real import first
            from langchain_community.chat_models import vertexai  # noqa: F401
        except (ImportError, AttributeError):
            # Inject a stub module so ragas can import without crashing
            stub = types.ModuleType("langchain_community.chat_models.vertexai")
            stub.ChatVertexAI = None  # placeholder — ragas only imports the name
            sys.modules["langchain_community.chat_models.vertexai"] = stub
            logger.debug("Patched missing langchain_community.chat_models.vertexai for ragas compatibility.")


def _check_ragas_installed() -> bool:
    _patch_missing_vertexai()
    try:
        import ragas  # noqa: F401
        return True
    except ImportError as e:
        logger.error("RAGAS import failed: %s  →  Run: pip install ragas datasets", e)
        return False
    except Exception as e:
        logger.error("Unexpected error importing RAGAS: %s", e)
        return False


def run_ragas(
    question: str,
    answer: str,
    contexts: list[str],
    verbose: bool = True,
) -> Optional[dict]:
    """
    Runs RAGAS reference-free evaluation on a single question/answer/contexts triple.

    Args:
        question : The user's original question.
        answer   : The chatbot's generated answer.
        contexts : List of retrieved context strings (from Qdrant + web).
        verbose  : Print scores to console if True.

    Returns:
        dict of metric_name → float score (0.0 – 1.0), or None if RAGAS unavailable.
    """
    if not _check_ragas_installed():
        logger.error(
            "RAGAS is not installed. Run: pip install ragas"
        )
        return None

    if not answer.strip():
        logger.warning("Empty answer — skipping RAGAS evaluation.")
        return None

    if not contexts:
        logger.warning("No contexts retrieved — RAGAS scores will be unreliable.")

    try:
        _patch_missing_vertexai()
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, LLMContextPrecisionWithoutReference
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        # Use the same LLM model as the chatbot for judging
        judge_llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
        judge_embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

        # RAGAS 0.2.x expects Dataset with these standard column names
        data = {
            "user_input": [question],
            "response": [answer],
            "retrieved_contexts": [contexts],   # list of lists
        }
        dataset = Dataset.from_dict(data)

        # Run evaluation — all 3 metrics are completely reference-free
        metric_context_prec = LLMContextPrecisionWithoutReference()
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, metric_context_prec],
            llm=judge_llm,
            embeddings=judge_embeddings,
            raise_exceptions=False,
        )

        # Extract scores cleanly via dataframe conversion
        df = result.to_pandas()
        row = df.to_dict(orient="records")[0] if not df.empty else {}

        scores = {
            "faithfulness": round(float(row.get("faithfulness", 0.0)), 4),
            "answer_relevancy": round(float(row.get("answer_relevancy", 0.0)), 4),
            "context_precision": round(float(row.get("llm_context_precision_without_reference", row.get("context_precision", 0.0))), 4),
        }

        logger.info(
            "RAGAS Evaluation Scores | question='%s' | faithfulness=%.4f | answer_relevancy=%.4f | context_precision=%.4f",
            question[:80],
            scores["faithfulness"],
            scores["answer_relevancy"],
            scores["context_precision"],
        )

        if verbose:
            _print_scores(question, scores)

        return scores

    except Exception as e:
        logger.error("RAGAS evaluation failed: %s", e)
        return None


def _print_scores(question: str, scores: dict) -> None:
    """Pretty-print RAGAS scores to console safely across all OS terminal encodings."""
    try:
        print("\n" + "=" * 60)
        print("[RAGAS Evaluation Results]")
        print(f"Question: {question[:80]}{'...' if len(question) > 80 else ''}")
        print("-" * 60)
        for metric, score in scores.items():
            bar = _score_bar(score)
            color = _score_color(score)
            label = metric.replace("_", " ").title()
            print(f"  {color}{label:<22}{score:.4f}  {bar}\033[0m")
        print("=" * 60 + "\n")
    except Exception:
        # Fallback if terminal does not support ANSI colors/characters
        print("\n=== RAGAS Evaluation Results ===")
        print(f"Question: {question[:80]}")
        for metric, score in scores.items():
            print(f"  {metric}: {score:.4f}")
        print("===============================\n")


def _score_bar(score: float, width: int = 20) -> str:
    """Render a simple progress bar."""
    filled = int(score * width)
    return "#" * filled + "-" * (width - filled)


def _score_color(score: float) -> str:
    """ANSI color based on score range."""
    if score >= 0.75:
        return "\033[92m"   # green
    elif score >= 0.50:
        return "\033[93m"   # yellow
    else:
        return "\033[91m"   # red
