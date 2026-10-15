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
