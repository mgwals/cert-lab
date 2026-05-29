from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from cert_lab.content import correct_option_id
from cert_lab.models import LabCompletion, QuestionAttempt


def grade_answers(
    questions: list[dict[str, Any]], submitted_answers: dict[str, str]
) -> list[dict[str, Any]]:
    results = []
    for question in questions:
        selected = submitted_answers.get(question["id"], "")
        correct = correct_option_id(question)
        option_text = {option["id"]: option["text"] for option in question["options"]}
        results.append(
            {
                "question": question,
                "selected_option": selected,
                "selected_text": option_text.get(selected, selected or "Sin respuesta"),
                "correct_option": correct,
                "correct_text": option_text[correct],
                "is_correct": selected == correct,
            }
        )
    return results


def latest_attempts(session: Session, cert_slug: str) -> dict[str, QuestionAttempt]:
    attempts = session.exec(
        select(QuestionAttempt)
        .where(QuestionAttempt.cert_slug == cert_slug)
        .order_by(QuestionAttempt.created_at, QuestionAttempt.id)
    ).all()
    latest: dict[str, QuestionAttempt] = {}
    for attempt in attempts:
        latest[attempt.question_id] = attempt
    return latest


def failed_question_ids(session: Session, cert_slug: str) -> set[str]:
    return {
        question_id
        for question_id, attempt in latest_attempts(session, cert_slug).items()
        if not attempt.is_correct
    }


def completed_lab_ids(session: Session, cert_slug: str) -> set[str]:
    completions = session.exec(
        select(LabCompletion).where(LabCompletion.cert_slug == cert_slug)
    ).all()
    return {completion.lab_id for completion in completions}


def certification_progress(session: Session, certification: dict[str, Any]) -> dict[str, Any]:
    cert_slug = certification["slug"]
    latest = latest_attempts(session, cert_slug)
    completed_labs = completed_lab_ids(session, cert_slug)
    correct_questions = {
        question_id for question_id, attempt in latest.items() if attempt.is_correct
    }
    failed_questions = {
        question_id for question_id, attempt in latest.items() if not attempt.is_correct
    }

    total_questions = len(certification["questions"])
    total_labs = len(certification["labs"])
    total_items = total_questions + total_labs
    completed_items = len(correct_questions) + len(completed_labs)
    mastery = round((completed_items / total_items) * 100) if total_items else 0

    domain_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "questions": 0,
            "correct_questions": 0,
            "failed_questions": 0,
            "labs": 0,
            "completed_labs": 0,
        }
    )
    for question in certification["questions"]:
        stats = domain_stats[question["domain"]]
        stats["questions"] += 1
        if question["id"] in correct_questions:
            stats["correct_questions"] += 1
        if question["id"] in failed_questions:
            stats["failed_questions"] += 1
    for lab in certification["labs"]:
        stats = domain_stats[lab["domain"]]
        stats["labs"] += 1
        if lab["id"] in completed_labs:
            stats["completed_labs"] += 1

    return {
        "mastery": mastery,
        "answered_questions": len(latest),
        "correct_questions": len(correct_questions),
        "failed_questions": len(failed_questions),
        "total_questions": total_questions,
        "completed_labs": len(completed_labs),
        "total_labs": total_labs,
        "domain_stats": domain_stats,
    }
