from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent


def default_content_path() -> Path:
    configured_path = os.environ.get("CERT_LAB_CONTENT_PATH")
    candidates = [
        Path(configured_path) if configured_path else None,
        Path.cwd() / "content" / "es" / "certifications.yml",
        PACKAGE_ROOT / "data" / "es" / "certifications.yml",
        PACKAGE_ROOT.parents[1] / "content" / "es" / "certifications.yml",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return Path(configured_path) if configured_path else candidates[1]


class ContentError(ValueError):
    """Raised when versioned study content is invalid."""


def _require_keys(item: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - set(item)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ContentError(f"{label} is missing required keys: {missing_list}")


def _validate_catalog(catalog: dict[str, Any]) -> None:
    if "certifications" not in catalog or not isinstance(catalog["certifications"], list):
        raise ContentError("catalog must contain a certifications list")

    seen_certifications: set[str] = set()
    for cert in catalog["certifications"]:
        _require_keys(
            cert,
            {
                "slug",
                "title",
                "short_title",
                "official_url",
                "description",
                "domains",
                "questions",
                "labs",
            },
            "certification",
        )
        slug = cert["slug"]
        if slug in seen_certifications:
            raise ContentError(f"duplicate certification slug: {slug}")
        seen_certifications.add(slug)

        domain_slugs = {domain["slug"] for domain in cert["domains"]}
        question_ids: set[str] = set()
        for question in cert["questions"]:
            _require_keys(
                question,
                {"id", "domain", "prompt", "options", "explanation"},
                f"question in {slug}",
            )
            if question["id"] in question_ids:
                raise ContentError(f"duplicate question id in {slug}: {question['id']}")
            question_ids.add(question["id"])
            if question["domain"] not in domain_slugs:
                raise ContentError(f"question {question['id']} references an unknown domain")
            correct_options = [option for option in question["options"] if option.get("correct")]
            if len(correct_options) != 1:
                raise ContentError(
                    f"question {question['id']} must have exactly one correct option"
                )

        lab_ids: set[str] = set()
        for lab in cert["labs"]:
            _require_keys(lab, {"id", "domain", "title", "goal", "tasks"}, f"lab in {slug}")
            if lab["id"] in lab_ids:
                raise ContentError(f"duplicate lab id in {slug}: {lab['id']}")
            lab_ids.add(lab["id"])
            if lab["domain"] not in domain_slugs:
                raise ContentError(f"lab {lab['id']} references an unknown domain")


@lru_cache(maxsize=4)
def load_catalog(path: Path | None = None) -> dict[str, Any]:
    path = path or default_content_path()
    with path.open(encoding="utf-8") as file:
        catalog = yaml.safe_load(file)
    if not isinstance(catalog, dict):
        raise ContentError("catalog root must be a mapping")
    _validate_catalog(catalog)
    return catalog


def get_certification(slug: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = catalog or load_catalog()
    for certification in catalog["certifications"]:
        if certification["slug"] == slug:
            return certification
    raise KeyError(slug)


def get_question(certification: dict[str, Any], question_id: str) -> dict[str, Any]:
    for question in certification["questions"]:
        if question["id"] == question_id:
            return question
    raise KeyError(question_id)


def correct_option_id(question: dict[str, Any]) -> str:
    return next(option["id"] for option in question["options"] if option["correct"])
