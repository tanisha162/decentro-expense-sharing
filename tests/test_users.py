def test_create_user_success(client):
    res = client.post("/users", json={"name": "Mohit", "email": "mohit@example.com"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["name"] == "Mohit"
    assert data["email"] == "mohit@example.com"

def test_create_user_blank_name_fails(client):
    res = client.post("/users", json={"name": "   "})
    assert res.status_code == 422

def test_list_users(client):
    client.post("/users", json={"name": "Mohit"})
    client.post("/users", json={"name": "Rahul"})
    client.post("/users", json={"name": "Ankit"})

    res = client.get("/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) == 3
    assert [u["name"] for u in users] == ["Mohit", "Rahul", "Ankit"]
