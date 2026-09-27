from __future__ import annotations

import csv
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from rag_hcmute.evaluation.metrics import QuestionOutcome, first_gold_rank, mean_reciprocal_rank, recall_at_k
from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.common import RetrievalHit

RECALL_K = 5
MRR_CONSIDERED_K = 10


@dataclass
class PilotQuestion:
    question_id: str
    question: str
    category: str
    answerability: str
    expected_document: str
    expected_chunk_id: str
    evidence_page: str

    @property
    def gold_chunk_ids(self) -> frozenset[str]:
        if not self.expected_chunk_id.strip():
            return frozenset()
        return frozenset(c.strip() for c in self.expected_chunk_id.split(";") if c.strip())


def load_pilot_questions(path: Path) -> list[PilotQuestion]:
    questions: list[PilotQuestion] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            questions.append(
                PilotQuestion(
                    question_id=row["question_id"],
                    question=row["question"],
                    category=row["category"],
                    answerability=row["answerability"],
                    expected_document=row.get("expected_document", ""),
                    expected_chunk_id=row.get("expected_chunk_id", ""),
                    evidence_page=row.get("evidence_page", ""),
                )
            )
    return questions


def run_pilot_evaluation(
    questions_path: Path,
    chunks_path: Path,
    snapshot_id: str,
    method_name: str,
    retriever,
    top_k: int = MRR_CONSIDERED_K,
    config: dict | None = None,
) -> dict:
    questions = load_pilot_questions(questions_path)
    per_question_results = []
    outcomes: list[QuestionOutcome] = []

    for q in questions:
        result = retriever.query(q.question, top_k=top_k)
        gold = q.gold_chunk_ids
        rank = first_gold_rank(result.hits, gold) if gold else None
        outcomes.append(QuestionOutcome(question_id=q.question_id, gold_chunk_ids=gold, hit_rank=rank))

        per_question_results.append(
            {
                "question_id": q.question_id,
                "question": q.question,
                "category": q.category,
                "answerability_label": q.answerability,
                "gold_chunk_ids": sorted(gold),
                "hit_rank": rank,
                "latency_ms": round(result.latency_ms, 3),
                "top_k": [hit.to_dict() for hit in result.hits],
            }
        )

    recall, recall_hits, recall_n = recall_at_k(outcomes, RECALL_K)
    mrr, mrr_n = mean_reciprocal_rank(outcomes)

    return {
        "run_id": f"{method_name}_{snapshot_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method": method_name,
        "snapshot_id": snapshot_id,
        "chunks_path": str(chunks_path),
        "questions_path": str(questions_path),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "config": config or {},
        "metrics": {
            "recall_at_5": {"value": recall, "hits": recall_hits, "denominator": recall_n},
            "mrr": {"value": mrr, "denominator": mrr_n, "considered_top_k": MRR_CONSIDERED_K},
        },
        "results": per_question_results,
    }
