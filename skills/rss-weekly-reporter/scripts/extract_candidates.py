#!/usr/bin/env python3
"""Extract first-pass weekly-report candidates from Academic Feed Manager JSON.

This script only uses RSS metadata: title, authors, abstract, source, URL, DOI,
and dates. It does not fetch full text.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


KEYWORD_GROUPS = {
    "core_psychometrics": [
        "psychometric", "psychometrics", "latent trait", "educational measurement",
        "psychological measurement", "psychological assessment",
        "factor analysis", "number of factors", "factor retention",
        "structural equation", "sem", "item response", "irt",
        "cognitive diagnosis", "cdm", "q-matrix", "attribute hierarchy",
        "knowledge tracing",
    ],
    "aberrant_response": [
        "aberrant", "person fit", "item fit", "rapid guessing",
        "careless", "response time", "cheating", "preknowledge",
        "item leakage", "change point", "mixture model", "anomaly detection",
    ],
    "current_projects": [
        "multilevel", "missing data", "imputation",
        "anova", "effect size", "power analysis", "depression",
        "suicide", "suicidal", "mental health",
    ],
    "transfer_ai": [
        "large language model", "llm", "transformer", "foundation model",
        "machine learning", "deep learning", "reinforcement learning",
        "representation learning", "sequence model", "lstm",
        "graph neural", "embedding",
    ],
}

HIGH_VALUE_SOURCES = [
    "Nature", "Science", "PNAS", "Psychometrika", "Educational and Psychological Measurement",
    "Applied Psychological Measurement", "Journal of Educational and Behavioral Statistics",
    "Multivariate Behavioral Research", "Structural Equation Modeling",
]


def norm(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def keyword_matches(text: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    if keyword.lower() in {"sem", "irt", "cdm", "llm", "lstm"}:
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return keyword.lower() in text


def score_paper(paper: dict) -> tuple[int, list[str]]:
    text = " ".join([
        norm(paper.get("title")),
        norm(paper.get("abstract")),
        norm(paper.get("source")),
    ]).lower()
    reasons: list[str] = []
    score = 0

    matched_groups = []
    for group, keywords in KEYWORD_GROUPS.items():
        hits = [kw for kw in keywords if keyword_matches(text, kw)]
        if hits:
            matched_groups.append(group)
            score += min(len(hits), 3)
            reasons.append(f"{group}: {', '.join(hits[:5])}")

    if "core_psychometrics" in matched_groups and "transfer_ai" in matched_groups:
        score += 5
        reasons.append("bridge: psychometrics/measurement + AI/ML/LLM")
    if "current_projects" in matched_groups and "transfer_ai" in matched_groups:
        score += 3
        reasons.append("bridge: current project + AI/ML/LLM")

    source = norm(paper.get("source"))
    if any(src.lower() in source.lower() for src in HIGH_VALUE_SOURCES):
        score += 1
        reasons.append(f"venue/source signal: {source}")

    return score, reasons


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: extract_candidates.py <latest_results.json> [limit]", file=sys.stderr)
        return 2

    path = Path(argv[1])
    limit = int(argv[2]) if len(argv) > 2 else 80
    data = json.loads(path.read_text(encoding="utf-8"))

    candidates = []
    for paper in data.get("papers", []):
        score, reasons = score_paper(paper)
        if score <= 0:
            continue
        candidates.append({
            "score": score,
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "source": paper.get("source", ""),
            "published": paper.get("published", ""),
            "url": paper.get("url", ""),
            "doi": paper.get("doi", ""),
            "abstract": paper.get("abstract", ""),
            "reasons": reasons,
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    output = {
        "run_id": data.get("run_id", ""),
        "created_at": data.get("created_at", ""),
        "finished_at": data.get("finished_at", ""),
        "candidate_count": len(candidates),
        "candidates": candidates[:limit],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
