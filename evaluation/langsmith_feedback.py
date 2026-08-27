"""
langsmith_feedback.py
---------------------
Pushes RAGAS scores back to LangSmith as structured feedback on a run.

Flow:
  1. After pipeline runs → LangSmith auto-captures a trace (Run ID)
  2. After RAGAS scores computed → we push them as feedback on that Run ID
  3. In LangSmith UI: each trace shows its RAGAS scores inline

Requires: LANGCHAIN_API_KEY set in .env
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


def push_scores_to_langsmith(
    run_id: str,
    scores: dict,
) -> bool:
    """
    Push RAGAS metric scores to a LangSmith run as feedback.

    Args:
        run_id : The LangSmith run ID of the traced pipeline execution.
        scores : Dict of metric_name → float, e.g. {"faithfulness": 0.87, ...}

    Returns:
        True if feedback was pushed successfully, False otherwise.
    """
    if not settings.langsmith_enabled:
        logger.info("LangSmith not configured — skipping feedback push.")
        return False

    try:
        from langsmith import Client

        client = Client(api_key=settings.LANGCHAIN_API_KEY)

        for metric_name, score in scores.items():
            client.create_feedback(
                run_id=run_id,
                key=f"ragas_{metric_name}",       # e.g. "ragas_faithfulness"
                score=score,
                comment=f"RAGAS {metric_name}: {score:.4f}",
                source_info={"evaluator": "ragas", "metric": metric_name},
            )

        logger.info(
            "Pushed %d RAGAS scores to LangSmith run %s: %s",
            len(scores),
            run_id[:8],
            scores,
        )
        return True

    except ImportError:
        logger.error("langsmith package not installed. Run: pip install langsmith")
        return False
    except Exception as e:
        logger.error("Failed to push feedback to LangSmith run %s: %s", run_id, e)
        return False


def get_latest_run_id(project_name: Optional[str] = None) -> Optional[str]:
    """
    Fetches the ID of the most recent LangSmith run in the configured project.
    Useful when you don't have the run_id captured directly.

    Returns:
        run_id string or None if not available.
    """
    if not settings.langsmith_enabled:
        return None

    try:
        from langsmith import Client

        client = Client(api_key=settings.LANGCHAIN_API_KEY)
        project = project_name or settings.LANGCHAIN_PROJECT

        runs = list(client.list_runs(
            project_name=project,
            execution_order=1,       # top-level runs only
            limit=1,
        ))

        if runs:
            run_id = str(runs[0].id)
            logger.info("Latest LangSmith run ID: %s", run_id[:8])
            return run_id

        logger.warning("No runs found in LangSmith project '%s'", project)
        return None

    except Exception as e:
        logger.error("Failed to fetch latest run ID: %s", e)
        return None
