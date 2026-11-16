def test_create_group(client):
    res = client.post("/groups", json={"name": "Goa Trip", "description": "Friends getaway"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["name"] == "Goa Trip"
    assert data["description"] == "Friends getaway"

def test_add_members_to_group(client):
    # Setup group & users
    g_res = client.post("/groups", json={"name": "Goa Trip"})
    g_id = g_res.json()["id"]

    u1 = client.post("/users", json={"name": "Mohit"}).json()["id"]
    u2 = client.post("/users", json={"name": "Rahul"}).json()["id"]

    # Add member with user_id
    res1 = client.post(f"/groups/{g_id}/members", json={"user_id": u1})
    assert res1.status_code == 200

    # Add member with group_id and user_id in body
    res2 = client.post(f"/groups/{g_id}/members", json={"group_id": g_id, "user_id": u2})
    assert res2.status_code == 200

    # List members
    members_res = client.get(f"/groups/{g_id}/members")
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 2
    names = [m["name"] for m in members]
    assert "Mohit" in names
    assert "Rahul" in names

def test_add_nonexistent_user_to_group(client):
    g_res = client.post("/groups", json={"name": "Goa Trip"})
    g_id = g_res.json()["id"]

    res = client.post(f"/groups/{g_id}/members", json={"user_id": 9999})
    assert res.status_code == 404

def test_add_member_conflicting_body_group_id_rejected(client):
    """A body group_id that disagrees with the path group_id must be
    rejected, not silently add the user to the other group (regression:
    POST /groups/1/members with {"group_id": 2, ...} added the user to
    group 2 while the URL said group 1)."""
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    g2 = client.post("/groups", json={"name": "Other Trip"}).json()["id"]
    u1 = client.post("/users", json={"name": "Mohit"}).json()["id"]

    res = client.post(f"/groups/{g1}/members", json={"group_id": g2, "user_id": u1})
    assert res.status_code == 400
    assert "does not match" in res.json()["detail"]

    # The user must not have landed in either group
    assert client.get(f"/groups/{g1}/members").json() == []
    assert client.get(f"/groups/{g2}/members").json() == []

    # A matching body group_id still works
    res_ok = client.post(f"/groups/{g1}/members", json={"group_id": g1, "user_id": u1})
    assert res_ok.status_code == 200
    assert [m["name"] for m in client.get(f"/groups/{g1}/members").json()] == ["Mohit"]
