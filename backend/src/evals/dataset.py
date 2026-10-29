from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EvalSample:
    id: str
    question: str
    reference_answer: str | None
    answerable: bool
    expected_filenames: list[str]
    labels: list[str]


@dataclass
class EvalDataset:
    dataset_version: str
    samples: list[EvalSample]


def default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "evals" / "datasets" / "golden-v1.json"


def load_dataset(path: Path | None = None) -> EvalDataset:
    p = path or default_dataset_path()
    raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    samples = [
        EvalSample(
            id=str(s["id"]),
            question=str(s["question"]),
            reference_answer=s.get("reference_answer"),
            answerable=bool(s.get("answerable", True)),
            expected_filenames=list(s.get("expected_filenames") or []),
            labels=list(s.get("labels") or []),
        )
        for s in raw.get("samples") or []
    ]
    return EvalDataset(
        dataset_version=str(raw.get("dataset_version") or p.stem),
        samples=samples,
    )
