import pytest


def test_register_success(client):
    res = client.post(
        "/auth/register",
        json={
            "name": "New Person",
            "email": "new.person@example.com",
            "password": "ValidPassword123!"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["email"] == "new.person@example.com"


def test_register_duplicate_email(client):
    # First registration
    client.post(
        "/auth/register",
        json={
            "name": "Dupe Person",
            "email": "duplicate@example.com",
            "password": "ValidPassword123!"
        }
    )
    # Second registration with same email
    res = client.post(
        "/auth/register",
        json={
            "name": "Dupe Person 2",
            "email": "duplicate@example.com",
            "password": "OtherPassword123!"
        }
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "name": "Login Tester",
            "email": "login.test@example.com",
            "password": "SecretPassword123!"
        }
    )
    res = client.post(
        "/auth/login",
        json={
            "email": "login.test@example.com",
            "password": "SecretPassword123!"
        }
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_invalid_password(client):
    res = client.post(
        "/auth/login",
        json={
            "email": "login.test@example.com",
            "password": "WrongPassword999!"
        }
    )
    assert res.status_code == 401


def test_protected_route_unauthenticated(client):
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_protected_route_authenticated(client, test_user_token):
    token, user = test_user_token
    res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == user["email"]


def test_profile_update(client, test_user_token):
    token, user = test_user_token
    # Get profile
    res = client.get(
        "/profile/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200

    # Update profile
    update_res = client.put(
        "/profile/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Jane Updated",
            "age_range": "36-50",
            "daily_practice_goal": 20,
            "font_size_preference": "large",
            "high_contrast": True
        }
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Jane Updated"
    assert updated_data["age_range"] == "36-50"
    assert updated_data["daily_practice_goal"] == 20
    assert updated_data["high_contrast"] is True
