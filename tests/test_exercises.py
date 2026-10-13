import pytest


def test_list_categories(client):
    res = client.get("/exercises/categories")
    assert res.status_code == 200
    categories = res.json()
    assert len(categories) >= 4
    slugs = [c["slug"] for c in categories]
    assert "word-practice" in slugs
    assert "phrase-practice" in slugs


def test_list_exercises_and_filters(client):
    res = client.get("/exercises/")
    assert res.status_code == 200
    exercises = res.json()
    assert len(exercises) > 0

    # Test filtering by category
    res_filtered = client.get("/exercises/?category=word-practice")
    assert res_filtered.status_code == 200
    words = res_filtered.json()
    assert len(words) > 0
    assert all(w["exercise_type"] == "word" or w["category_name"] == "Word Practice" for w in words)

    # Test filtering by difficulty
    res_diff = client.get("/exercises/?difficulty=beginner")
    assert res_diff.status_code == 200
    beg = res_diff.json()
    assert all(b["difficulty"] == "beginner" for b in beg)

    # Test keyword search
    res_search = client.get("/exercises/?search=Water")
    assert res_search.status_code == 200
    matched = res_search.json()
    assert len(matched) >= 1
    assert any("Water" in m["title"] or "water" in m["target_text"].lower() for m in matched)


def test_bookmark_exercise(client, test_user_token):
    token, user = test_user_token
    # Get first exercise
    ex_res = client.get("/exercises/")
    ex_id = ex_res.json()[0]["id"]

    # Toggle bookmark
    bm_res = client.post(
        f"/exercises/{ex_id}/bookmark",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert bm_res.status_code == 200
    assert bm_res.json()["is_bookmarked"] is True

    # Check bookmarked list
    list_bm = client.get(
        "/exercises/bookmarked/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_bm.status_code == 200
    bm_ids = [e["id"] for e in list_bm.json()]
    assert ex_id in bm_ids

    # Toggle off
    bm_res2 = client.post(
        f"/exercises/{ex_id}/bookmark",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert bm_res2.status_code == 200
    assert bm_res2.json()["is_bookmarked"] is False
