import pytest


def test_speech_feedback_exact_match(client):
    res = client.post(
        "/practice/feedback",
        json={
            "target_text": "Good morning",
            "spoken_text": "Good morning",
            "exercise_type": "phrase"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["similarity_score"] == 100.0
    assert data["is_exact_match"] is True
    assert len(data["missing_words"]) == 0
    assert "disclaimer" in data


def test_speech_feedback_partial_match(client):
    res = client.post(
        "/practice/feedback",
        json={
            "target_text": "I would like some water",
            "spoken_text": "I would like water",
            "exercise_type": "phrase"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert 60.0 <= data["similarity_score"] < 100.0
    assert data["is_exact_match"] is False
    assert "some" in data["missing_words"]
    assert len(data["matched_words"]) >= 3


def test_practice_session_lifecycle(client, test_user_token):
    token, user = test_user_token
    # 1. Start session
    start_res = client.post(
        "/practice/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": 1}
    )
    assert start_res.status_code == 201
    session_id = start_res.json()["id"]
    assert start_res.json()["completion_status"] == "in_progress"

    # 2. Record response
    resp_res = client.post(
        f"/practice/sessions/{session_id}/responses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "exercise_id": 1,
            "target_text": "Water",
            "recognized_text": "Water",
            "similarity_score": 100.0,
            "attempt_number": 1
        }
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["similarity_score"] == 100.0

    # 3. Complete session
    comp_res = client.post(
        f"/practice/sessions/{session_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"duration_seconds": 120}
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["completion_status"] == "completed"
    assert comp_data["exercise_count"] == 1
    assert comp_data["duration_seconds"] == 120


def test_cross_user_isolation(client, test_user_token, second_user_token):
    token_1, user_1 = test_user_token
    token_2, user_2 = second_user_token

    # User 1 starts session
    s1_res = client.post(
        "/practice/sessions",
        headers={"Authorization": f"Bearer {token_1}"},
        json={"category_id": 1}
    )
    s1_id = s1_res.json()["id"]

    # User 2 tries to access User 1's session -> must be 403 Forbidden
    access_res = client.get(
        f"/practice/sessions/{s1_id}",
        headers={"Authorization": f"Bearer {token_2}"}
    )
    assert access_res.status_code == 403

    # User 2 tries to submit response to User 1's session -> must be 403 Forbidden
    submit_res = client.post(
        f"/practice/sessions/{s1_id}/responses",
        headers={"Authorization": f"Bearer {token_2}"},
        json={
            "target_text": "Test",
            "recognized_text": "Test",
            "similarity_score": 90.0
        }
    )
    assert submit_res.status_code == 403


def test_prevent_duplicate_blank_sessions(client, test_user_token):
    token, user = test_user_token
    headers = {"Authorization": f"Bearer {token}"}

    # First session creation
    res1 = client.post("/practice/sessions", headers=headers, json={"language": "en-US"})
    assert res1.status_code == 201
    s1_id = res1.json()["id"]

    # Immediate second session creation without recording any responses
    res2 = client.post("/practice/sessions", headers=headers, json={"language": "en-US"})
    assert res2.status_code == 201
    s2_id = res2.json()["id"]

    # Must reuse the same active blank session to avoid polluting database
    assert s1_id == s2_id

