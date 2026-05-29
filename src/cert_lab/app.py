from __future__ import annotations

import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from cert_lab.content import get_certification, get_question, load_catalog
from cert_lab.db import engine, get_session, init_db
from cert_lab.models import LabCompletion, QuestionAttempt
from cert_lab.scoring import (
    certification_progress,
    completed_lab_ids,
    failed_question_ids,
    grade_answers,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=PACKAGE_ROOT / "templates")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db(engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Cert Lab", lifespan=lifespan)
    app.mount(
        "/static",
        StaticFiles(directory=PACKAGE_ROOT / "static"),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        session: Annotated[Session, Depends(get_session)],
    ) -> HTMLResponse:
        catalog = load_catalog()
        certifications = [
            {
                **certification,
                "progress": certification_progress(session, certification),
            }
            for certification in catalog["certifications"]
        ]
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"certifications": certifications},
        )

    @app.get("/certifications/{cert_slug}", response_class=HTMLResponse)
    def certification_detail(
        cert_slug: str,
        request: Request,
        session: Annotated[Session, Depends(get_session)],
    ) -> HTMLResponse:
        certification = _load_certification_or_404(cert_slug)
        progress = certification_progress(session, certification)
        completed_labs = completed_lab_ids(session, cert_slug)
        return templates.TemplateResponse(
            request,
            "certification.html",
            {
                "certification": certification,
                "progress": progress,
                "completed_labs": completed_labs,
            },
        )

    @app.get("/quiz/{cert_slug}", response_class=HTMLResponse)
    def quiz(
        cert_slug: str,
        request: Request,
        session: Annotated[Session, Depends(get_session)],
        mode: str = "all",
    ) -> HTMLResponse:
        certification = _load_certification_or_404(cert_slug)
        questions = _select_quiz_questions(certification, session, mode)
        return templates.TemplateResponse(
            request,
            "quiz.html",
            {
                "certification": certification,
                "questions": questions,
                "mode": mode,
                "empty_failed_review": mode == "failed" and not questions,
            },
        )

    @app.post("/quiz/{cert_slug}", response_class=HTMLResponse)
    async def submit_quiz(
        cert_slug: str,
        request: Request,
        session: Annotated[Session, Depends(get_session)],
    ) -> HTMLResponse:
        certification = _load_certification_or_404(cert_slug)
        form = await request.form()
        question_ids = form.getlist("question_id")
        if not question_ids:
            raise HTTPException(status_code=400, detail="No questions submitted")
        try:
            questions = [get_question(certification, question_id) for question_id in question_ids]
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Invalid question submitted") from exc
        answers = {
            question_id: str(form.get(f"answer_{question_id}", "")) for question_id in question_ids
        }
        results = grade_answers(questions, answers)

        for result in results:
            session.add(
                QuestionAttempt(
                    cert_slug=cert_slug,
                    question_id=result["question"]["id"],
                    selected_option=result["selected_option"],
                    is_correct=result["is_correct"],
                )
            )
        session.commit()

        correct_count = sum(1 for result in results if result["is_correct"])
        return templates.TemplateResponse(
            request,
            "quiz_result.html",
            {
                "certification": certification,
                "results": results,
                "correct_count": correct_count,
                "total_count": len(results),
            },
        )

    @app.post("/certifications/{cert_slug}/labs/{lab_id}/toggle")
    def toggle_lab(
        cert_slug: str,
        lab_id: str,
        session: Annotated[Session, Depends(get_session)],
        completed: Annotated[bool, Form()] = False,
    ) -> RedirectResponse:
        certification = _load_certification_or_404(cert_slug)
        if lab_id not in {lab["id"] for lab in certification["labs"]}:
            raise HTTPException(status_code=404, detail="Lab not found")

        existing = session.exec(
            select(LabCompletion).where(
                LabCompletion.cert_slug == cert_slug,
                LabCompletion.lab_id == lab_id,
            )
        ).first()

        if completed and existing is None:
            session.add(LabCompletion(cert_slug=cert_slug, lab_id=lab_id))
        elif not completed and existing is not None:
            session.delete(existing)
        session.commit()
        return RedirectResponse(f"/certifications/{cert_slug}", status_code=303)

    return app


def _load_certification_or_404(cert_slug: str) -> dict[str, Any]:
    try:
        return get_certification(cert_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Certification not found") from exc


def _select_quiz_questions(
    certification: dict[str, Any],
    session: Session,
    mode: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if mode not in {"all", "failed"}:
        raise HTTPException(status_code=400, detail="Unsupported quiz mode")

    questions = certification["questions"]
    if mode == "failed":
        failed_ids = failed_question_ids(session, certification["slug"])
        questions = [question for question in questions if question["id"] in failed_ids]

    selected = list(questions)
    random.Random().shuffle(selected)
    return selected[:limit]


app = create_app()
