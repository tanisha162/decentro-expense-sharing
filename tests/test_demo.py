"""Demo seed endpoint: idempotency and per-expense seeding."""


def test_seed_is_idempotent(client):
    client.post("/api/demo/seed")
    client.post("/api/demo/seed")
    groups = client.get("/groups").json()
    goa = next(g for g in groups if g["name"] == "Goa Trip")
    expenses = client.get(f"/groups/{goa['id']}/expenses").json()
    assert sorted(e["description"] for e in expenses) == [
        "Airport Taxi",
        "Beach Shack Breakfast",
        "Dinner",
    ]


def test_seed_not_blocked_by_user_expense_named_dinner(client):
    # A user expense literally named "Dinner" in the Goa Trip group used
    # to make /api/demo/seed skip all three seed expenses (it gated them
    # on the Dinner expense alone) while still reporting success, leaving
    # the demo data incomplete.
    user = client.post("/users", json={"name": "Zed"}).json()
    group = client.post("/groups", json={"name": "Goa Trip"}).json()
    client.post(f"/groups/{group['id']}/members", json={"user_id": user["id"]})
    r = client.post("/expenses", json={
        "group_id": group["id"], "paid_by": user["id"], "amount": 50,
        "description": "Dinner", "split_type": "EQUAL"})
    assert r.status_code == 201

    seed = client.post("/api/demo/seed")
    assert seed.status_code == 200

    expenses = client.get(f"/groups/{group['id']}/expenses").json()
    descriptions = sorted(e["description"] for e in expenses)
    assert "Beach Shack Breakfast" in descriptions
    assert "Airport Taxi" in descriptions
    # The user's own Dinner expense is untouched, not duplicated.
    assert descriptions.count("Dinner") == 1
