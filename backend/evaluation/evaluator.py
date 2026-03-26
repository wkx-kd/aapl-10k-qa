"""Evaluation framework for the RAG system."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).parent / "results"


class Evaluator:
    """Evaluates the RAG system across multiple dimensions."""

    def __init__(self, intent_router, sql_store, vector_store, graph_store, llm_client):
        self.router = intent_router
        self.sql_store = sql_store
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.llm = llm_client

    def load_test_questions(
        self, categories: Optional[list[str]] = None
    ) -> list[dict]:
        """Load test questions, optionally filtered by category."""
        path = Path(__file__).parent / "test_questions.json"
        with open(path) as f:
            questions = json.load(f)

        if categories:
            questions = [q for q in questions if q["category"] in categories]

        return questions

    async def run_evaluation(
        self, categories: Optional[list[str]] = None, top_k: int = 5
    ) -> dict:
        """Run full evaluation and return results."""
        questions = self.load_test_questions(categories)
        run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting evaluation run {run_id} with {len(questions)} questions")

        per_question = []
        intent_correct = 0
        keyword_matches_total = 0
        keyword_possible_total = 0

        for i, q in enumerate(questions):
            logger.info(f"  [{i+1}/{len(questions)}] {q['question'][:60]}...")
            result = await self._evaluate_single(q, top_k)
            per_question.append(result)

            if result.get("intent_correct"):
                intent_correct += 1
            keyword_matches_total += result.get("keyword_matches", 0)
            keyword_possible_total += result.get("keyword_possible", 0)

        # Aggregate metrics
        n = len(questions)
        aggregate = {
            "total_questions": n,
            "intent_accuracy": round(intent_correct / n, 3) if n else 0,
            "keyword_match_rate": (
                round(keyword_matches_total / keyword_possible_total, 3)
                if keyword_possible_total
                else 0
            ),
            "by_category": self._aggregate_by_category(per_question),
        }

        result = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "top_k": top_k,
                "categories": categories,
                "llm_model": self.llm.model,
            },
            "aggregate": aggregate,
            "per_question": per_question,
        }

        # Save results
        EVAL_DIR.mkdir(exist_ok=True)
        output_path = EVAL_DIR / f"{run_id}.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Evaluation complete. Results saved to {output_path}")
        self._print_summary(result)

        return result

    async def _evaluate_single(self, question: dict, top_k: int) -> dict:
        """Evaluate a single question."""
        q_text = question["question"]
        start = time.time()

        # Step 1: Classify intent
        predicted_intent = await self.router.classify_intent(q_text)
        intent_correct = predicted_intent == question.get("expected_intent", "")

        # Step 2: Collect full response
        full_response = ""
        sources = []

        async for event in self.router.route_and_generate(
            query=q_text, top_k=top_k
        ):
            if event["type"] == "token":
                full_response += event.get("content", "")
            elif event["type"] == "sources":
                sources = event.get("sources", [])

        elapsed = time.time() - start

        # Step 3: Check keyword matches
        expected_keywords = question.get("expected_answer_contains", [])
        response_lower = full_response.lower()
        keyword_hits = sum(
            1 for kw in expected_keywords if kw.lower() in response_lower
        )

        return {
            "id": question["id"],
            "question": q_text,
            "category": question["category"],
            "expected_intent": question.get("expected_intent"),
            "predicted_intent": predicted_intent,
            "intent_correct": intent_correct,
            "answer": full_response[:1000],
            "answer_length": len(full_response),
            "sources_count": len(sources),
            "source_types": list(set(s.get("type", "") for s in sources)),
            "keyword_matches": keyword_hits,
            "keyword_possible": len(expected_keywords),
            "matched_keywords": [
                kw for kw in expected_keywords if kw.lower() in response_lower
            ],
            "elapsed_seconds": round(elapsed, 2),
        }

    def _aggregate_by_category(self, results: list[dict]) -> dict:
        """Aggregate metrics by question category."""
        categories: dict[str, list] = {}
        for r in results:
            cat = r["category"]
            categories.setdefault(cat, []).append(r)

        summary = {}
        for cat, items in categories.items():
            n = len(items)
            summary[cat] = {
                "count": n,
                "intent_accuracy": round(
                    sum(1 for i in items if i["intent_correct"]) / n, 3
                ),
                "keyword_match_rate": round(
                    sum(i["keyword_matches"] for i in items)
                    / max(sum(i["keyword_possible"] for i in items), 1),
                    3,
                ),
                "avg_response_time": round(
                    sum(i["elapsed_seconds"] for i in items) / n, 2
                ),
            }
        return summary

    def _print_summary(self, result: dict):
        """Print evaluation summary to logger."""
        agg = result["aggregate"]
        logger.info("=" * 60)
        logger.info(f"Evaluation Results ({result['run_id']})")
        logger.info("=" * 60)
        logger.info(f"Total Questions: {agg['total_questions']}")
        logger.info(f"Intent Accuracy: {agg['intent_accuracy']:.1%}")
        logger.info(f"Keyword Match Rate: {agg['keyword_match_rate']:.1%}")
        logger.info("")
        logger.info("Per-Category Breakdown:")
        for cat, metrics in agg["by_category"].items():
            logger.info(
                f"  {cat}: "
                f"Intent={metrics['intent_accuracy']:.0%}, "
                f"Keywords={metrics['keyword_match_rate']:.0%}, "
                f"AvgTime={metrics['avg_response_time']:.1f}s"
            )
        logger.info("=" * 60)
