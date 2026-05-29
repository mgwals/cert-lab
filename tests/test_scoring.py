from cert_lab.content import correct_option_id, get_certification, load_catalog
from cert_lab.scoring import grade_answers


def test_grade_answers_marks_correct_and_wrong_answers() -> None:
    certification = get_certification("github-foundations", load_catalog())
    questions = certification["questions"][:2]
    submitted = {
        questions[0]["id"]: correct_option_id(questions[0]),
        questions[1]["id"]: "not-correct",
    }

    results = grade_answers(questions, submitted)

    assert [result["is_correct"] for result in results] == [True, False]
    assert results[0]["selected_option"] == results[0]["correct_option"]
    assert results[0]["selected_text"]
    assert results[0]["correct_text"]
