import pytest
from fastapi.testclient import TestClient
from services.speech_feedback import evaluate_speech_similarity, normalize_text, is_tamil_text


def test_tamil_text_normalization():
    """Verify Unicode NFC normalization and punctuation removal for Tamil text."""
    target = "தண்ணீர்!"
    normalized = normalize_text(target)
    assert normalized == "தண்ணீர்"
    assert is_tamil_text("தண்ணீர்") is True
    assert is_tamil_text("Water") is False


def test_tamil_speech_evaluation_exact_match():
    """Verify exact match evaluation for key Tamil words."""
    words = ["தண்ணீர்", "அம்மா", "வீடு", "உதவி", "நன்றி"]
    for word in words:
        result = evaluate_speech_similarity(target_text=word, spoken_text=word, exercise_type="word", language="ta-IN")
        assert result.is_exact_match is True
        assert result.similarity_score == 100.0
        assert "மிகவும் நன்று" in result.suggestion or "அருமையாக" in result.suggestion
        assert "மருத்துவ மதிப்பீடு அல்ல" in result.disclaimer


def test_tamil_speech_evaluation_sandhi_variant():
    """Verify phrase matching with sandhi/spacing variants (e.g., with/without euphonic 'த்')."""
    target = "எனக்குத் தண்ணீர் வேண்டும்."
    spoken = "எனக்கு தண்ணீர் வேண்டும்"
    result = evaluate_speech_similarity(target_text=target, spoken_text=spoken, exercise_type="phrase", language="ta-IN")
    assert result.similarity_score >= 90.0
    assert "மிகவும் நன்று" in result.suggestion or "அருமையாக" in result.suggestion


def test_tamil_speech_evaluation_empty_input():
    """Verify empty/silent recognition returns supportive Tamil guidance without penalties."""
    result = evaluate_speech_similarity(target_text="தண்ணீர்", spoken_text="", exercise_type="word", language="ta-IN")
    assert result.similarity_score == 0.0
    assert result.is_exact_match is False
    assert "உங்கள் குரலைத் தெளிவாகக் கேட்க முடியவில்லை" in result.suggestion


def test_list_exercises_by_language(client: TestClient):
    """Verify filtering exercises by language code."""
    # Fetch Tamil exercises
    res_ta = client.get("/exercises/?language=ta-IN")
    assert res_ta.status_code == 200
    data_ta = res_ta.json()
    assert len(data_ta) > 0
    for ex in data_ta:
        assert ex["language"] == "ta-IN"
        assert ex["english_meaning"] is not None

    # Fetch English exercises
    res_en = client.get("/exercises/?language=en-US")
    assert res_en.status_code == 200
    data_en = res_en.json()
    assert len(data_en) > 0
    for ex in data_en:
        assert ex["language"] == "en-US"


def test_tamil_session_and_progress_tracking(client: TestClient, test_user_token):
    """Verify language stored with practice session and separate progress filtering."""
    token, user = test_user_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start a Tamil practice session
    sess_res = client.post("/practice/sessions", json={"language": "ta-IN"}, headers=headers)
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]
    assert sess_res.json()["language"] == "ta-IN"

    # 2. Record a Tamil response
    resp_res = client.post(
        f"/practice/sessions/{session_id}/responses",
        json={
            "target_text": "தண்ணீர்",
            "recognized_text": "தண்ணீர்",
            "similarity_score": 100.0,
            "attempt_number": 1,
            "language": "ta-IN"
        },
        headers=headers
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["language"] == "ta-IN"

    # 3. Complete the session
    comp_res = client.post(
        f"/practice/sessions/{session_id}/complete",
        json={"duration_seconds": 60},
        headers=headers
    )
    assert comp_res.status_code == 200

    # 4. Filter history by Tamil
    hist_ta = client.get("/progress/history?language=ta-IN", headers=headers)
    assert hist_ta.status_code == 200
    ta_data = hist_ta.json()["data"]
    assert len(ta_data) >= 1
    assert any(s["session_id"] == session_id for s in ta_data)

    # 5. Export CSV with Tamil content
    csv_res = client.get("/progress/export?language=ta-IN", headers=headers)
    assert csv_res.status_code == 200
    # Decode as UTF-8 (accounting for potential BOM)
    content = csv_res.content.decode("utf-8-sig")
    assert "Language" in content
    assert "English Meaning" in content
    assert "தண்ணீர்" in content
