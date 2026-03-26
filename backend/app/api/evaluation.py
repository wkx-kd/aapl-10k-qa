"""Evaluation API endpoints."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request, BackgroundTasks

from app.models.schemas import EvalRequest

logger = logging.getLogger(__name__)
router = APIRouter()

RESULTS_DIR = Path(__file__).parent.parent.parent / "evaluation" / "results"


@router.post("/eval/run")
async def run_evaluation(
    request: Request,
    eval_req: EvalRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger an evaluation run (runs in background)."""
    from evaluation.evaluator import Evaluator

    evaluator = Evaluator(
        intent_router=request.app.state.pipeline.router,
        sql_store=request.app.state.sql_store,
        vector_store=request.app.state.vector_store,
        graph_store=request.app.state.graph_store,
        llm_client=request.app.state.llm_client,
    )

    async def run():
        await evaluator.run_evaluation(
            categories=eval_req.categories,
            top_k=eval_req.top_k,
        )

    background_tasks.add_task(lambda: __import__("asyncio").run(run()))
    return {"status": "started", "message": "Evaluation running in background"}


@router.get("/eval/results")
async def get_latest_results():
    """Get the latest evaluation results."""
    RESULTS_DIR.mkdir(exist_ok=True)
    files = sorted(RESULTS_DIR.glob("eval_*.json"), reverse=True)
    if not files:
        return {"error": "No evaluation results found. Run an evaluation first."}

    with open(files[0]) as f:
        return json.load(f)


@router.get("/eval/results/{run_id}")
async def get_results_by_id(run_id: str):
    """Get evaluation results for a specific run."""
    path = RESULTS_DIR / f"{run_id}.json"
    if not path.exists():
        return {"error": f"Results not found for run_id: {run_id}"}

    with open(path) as f:
        return json.load(f)
