from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from cert_lab.app import app
from cert_lab.db import get_session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_dashboard_loads_without_existing_database_rows(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Panel de certificaciones" in response.text
    assert "GitHub Foundations" in response.text


def test_quiz_submission_persists_failed_questions_for_review(client: TestClient) -> None:
    quiz = client.get("/quiz/github-foundations")
    assert quiz.status_code == 200

    question_ids = _extract_hidden_question_ids(quiz.text)
    form_data = {"question_id": question_ids}
    form_data.update({f"answer_{question_id}": "wrong" for question_id in question_ids})

    result = client.post("/quiz/github-foundations", data=form_data)
    review = client.get("/quiz/github-foundations?mode=failed")

    assert result.status_code == 200
    assert f"Resultado: 0/{len(question_ids)}" in result.text
    assert review.status_code == 200
    assert "Repaso de fallos" in review.text
    assert "No hay fallos activos" not in review.text


def test_lab_completion_updates_certification_page(client: TestClient) -> None:
    response = client.post(
        "/certifications/pcep/labs/py-lab-01/toggle",
        data={"completed": "true"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "1/3" in response.text
    assert "Marcar pendiente" in response.text


def test_quiz_submission_rejects_unknown_question_id(client: TestClient) -> None:
    response = client.post(
        "/quiz/github-foundations",
        data={"question_id": "not-real", "answer_not-real": "A"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid question submitted"


def _extract_hidden_question_ids(html: str) -> list[str]:
    marker = 'name="question_id" value="'
    values = []
    cursor = 0
    while True:
        start = html.find(marker, cursor)
        if start == -1:
            return values
        value_start = start + len(marker)
        value_end = html.find('"', value_start)
        values.append(html[value_start:value_end])
        cursor = value_end + 1
