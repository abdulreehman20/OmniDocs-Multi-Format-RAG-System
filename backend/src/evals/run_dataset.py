"""CLI: uv run python -m src.evals.run_dataset [--dataset PATH] [--max N] [--llm]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlmodel import Session

from src.config import get_settings
from src.db.session import engine
from src.evals.runner import run_eval_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run golden RAG evaluation dataset")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to dataset JSON (default: evals/datasets/golden-v1.json)",
    )
    parser.add_argument("--max", type=int, default=None, help="Max samples")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use live ChatOpenRouter + optional RAGAS (costs tokens)",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    with Session(engine) as session:
        run = run_eval_dataset(
            session,
            settings,
            dataset_path=args.dataset,
            max_samples=args.max,
            use_llm=bool(args.llm),
        )
    print(
        json.dumps(
            {
                "id": run.id,
                "dataset_version": run.dataset_version,
                "status": run.status,
                "sample_count": run.sample_count,
                "aggregate_metrics": run.aggregate_metrics,
                "correlation_id": run.correlation_id,
            },
            indent=2,
        )
    )
    return 0 if run.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
