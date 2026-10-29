from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from src.ai.rag.citations import validate_citations
from src.ai.rag.generation import stream_answer_tokens
from src.ai.rag.prompts import FALLBACK_GROUNDED_TEMPLATE
from src.ai.rag.types import RetrievedSource
from src.config import Settings
from src.db.models import EvalRun
from src.evals.dataset import EvalDataset, EvalSample, load_dataset
from src.evals.metrics import abstention_quality, aggregate_custom_metrics, citation_validity_score

logger = logging.getLogger(__name__)


def _fake_sources_for_sample(sample: EvalSample) -> list[RetrievedSource]:
    if not sample.answerable:
        return []
    sources: list[RetrievedSource] = []
    for i, name in enumerate(sample.expected_filenames or ["fixture.md"], start=1):
        text = sample.reference_answer or "fixture context"
        sources.append(
            RetrievedSource(
                label=f"S{i}",
                chunk_id=f"chunk-{sample.id}-{i}",
                vector_id=f"vec-{sample.id}-{i}",
                document_id=f"doc-{name}",
                owner_id="eval",
                generation=1,
                filename=name,
                source_type="markdown",
                locator={},
                text=text,
                score=1.0,
                token_estimate=max(1, len(text) // 4),
            )
        )
    return sources


def _synthetic_answer(sample: EvalSample, sources: list[RetrievedSource]) -> str:
    if not sample.answerable or not sources:
        return (
            "I couldn't find enough information in the selected documents "
            "to answer that reliably."
        )
    cite = " ".join(f"[{s.label}]" for s in sources[:2])
    return f"{sample.reference_answer} {cite}".strip()


def _try_ragas_scores(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    reference: str | None,
    settings: Settings,
) -> dict[str, float]:
    """Best-effort RAGAS; returns empty dict if unavailable or on failure."""
    if not settings.openrouter_api_key:
        return {}
    try:
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        from datasets import Dataset
    except Exception:
        logger.info("ragas/datasets not usable; skipping RAGAS metrics")
        return {}

    try:
        row = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts or [""]],
            "ground_truth": [reference or ""],
        }
        ds = Dataset.from_dict(row)
        result = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        scores = dict(result)
        return {k: float(v) for k, v in scores.items() if isinstance(v, (int, float))}
    except Exception:
        logger.warning("ragas evaluate failed", exc_info=True)
        return {}


def run_eval_dataset(
    session: Session,
    settings: Settings,
    *,
    dataset_path: Path | None = None,
    max_samples: int | None = None,
    use_llm: bool = False,
    correlation_id: str | None = None,
) -> EvalRun:
    dataset: EvalDataset = load_dataset(dataset_path)
    limit = max_samples or settings.eval_max_samples
    samples = dataset.samples[:limit]

    run = EvalRun(
        id=str(uuid4()),
        dataset_version=dataset.dataset_version,
        status="running",
        chat_model_id=settings.chat_model_id,
        eval_model_id=settings.eval_model_id,
        prompt_version="grounded_chat",
        embedding_model_id=settings.embedding_model_id,
        retrieval_policy_version=settings.retrieval_policy_version,
        sample_count=len(samples),
        correlation_id=correlation_id or str(uuid4()),
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    sample_results: list[dict[str, Any]] = []
    try:
        for sample in samples:
            sources = _fake_sources_for_sample(sample)
            if use_llm and sources:
                answer = "".join(
                    stream_answer_tokens(
                        settings,
                        system_template=FALLBACK_GROUNDED_TEMPLATE,
                        sources=sources,
                        history=[],
                        question=sample.question,
                    )
                )
            else:
                answer = _synthetic_answer(sample, sources)

            custom = {
                "citation_validity": citation_validity_score(answer, sources),
                "abstention_quality": abstention_quality(
                    answerable=sample.answerable, answer=answer
                ),
            }
            ragas = _try_ragas_scores(
                question=sample.question,
                answer=answer,
                contexts=[s.text for s in sources],
                reference=sample.reference_answer,
                settings=settings,
            ) if use_llm else {}

            sample_results.append(
                {
                    "id": sample.id,
                    "question": sample.question,
                    "answerable": sample.answerable,
                    "answer": answer,
                    "validated_citations": [
                        s.label for s in validate_citations(answer, sources)
                    ],
                    **custom,
                    "ragas": ragas,
                }
            )

        custom_agg = aggregate_custom_metrics(sample_results)
        ragas_keys = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
        ragas_agg: dict[str, float] = {}
        for key in ragas_keys:
            vals = [
                float(r["ragas"][key])
                for r in sample_results
                if isinstance(r.get("ragas"), dict) and key in r["ragas"]
            ]
            if vals:
                ragas_agg[key] = sum(vals) / len(vals)

        run.aggregate_metrics = {**custom_agg, **ragas_agg}
        run.sample_results = sample_results
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        session.add(run)
        session.commit()
        session.refresh(run)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.sample_results = sample_results
        run.finished_at = datetime.now(UTC)
        session.add(run)
        session.commit()
        session.refresh(run)
        raise
