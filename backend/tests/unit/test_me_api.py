from src.db.models import User


def test_get_and_patch_me(client, session, auth_header_user_a):
    session.add(User(id="user-a", email="a@example.com", display_name="A"))
    session.commit()

    res = client.get("/api/v1/me", headers=auth_header_user_a)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "user-a"
    assert body["email"] == "a@example.com"

    patched = client.patch(
        "/api/v1/me",
        headers=auth_header_user_a,
        json={"display_name": "Ada", "preferences": {"cite_first": True}},
    )
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "Ada"
    assert patched.json()["preferences"]["cite_first"] is True
