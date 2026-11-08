def test_unread_notification_count_is_available_to_the_signed_in_user(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "procurement@apex.com", "password": "Password123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        "/api/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json()["unread_count"], int)


def test_unread_notification_count_requires_authentication(client):
    response = client.get("/api/notifications/count")

    assert response.status_code == 401
