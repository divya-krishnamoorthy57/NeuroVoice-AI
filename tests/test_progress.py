import pytest


def test_dashboard_and_progress_flow(client, test_user_token):
    token, user = test_user_token

    # Start and complete a session with a response
    s_res = client.post(
        "/practice/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": 1}
    )
    s_id = s_res.json()["id"]

    client.post(
        f"/practice/sessions/{s_id}/responses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "target_text": "Hello",
            "recognized_text": "Hello",
            "similarity_score": 95.0,
            "attempt_number": 1
        }
    )

    client.post(
        f"/practice/sessions/{s_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"duration_seconds": 60}
    )

    # Check Dashboard
    dash_res = client.get(
        "/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_sessions_completed"] >= 1
    assert dash_data["total_completed_exercises"] >= 1
    assert dash_data["average_accuracy"] > 0
    assert dash_data["current_streak_days"] >= 1

    # Check Progress summary
    prog_res = client.get(
        "/progress/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["total_sessions"] >= 1
    assert prog_data["total_exercises"] >= 1
    assert len(prog_data["category_breakdown"]) > 0

    # Test CSV export
    csv_res = client.get(
        "/progress/export",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Target Text" in csv_res.text
    assert "Hello" in csv_res.text


def test_admin_authorization(client, test_user_token, admin_user_token):
    user_token, _ = test_user_token

    # Regular user attempting admin endpoint -> must fail with 403
    unauth_res = client.get(
        "/admin/stats",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert unauth_res.status_code == 403

    # Admin user accessing admin endpoint -> must succeed with 200
    auth_res = client.get(
        "/admin/stats",
        headers={"Authorization": f"Bearer {admin_user_token}"}
    )
    assert auth_res.status_code == 200
    stats = auth_res.json()
    assert "total_users" in stats
    assert "total_exercises" in stats
