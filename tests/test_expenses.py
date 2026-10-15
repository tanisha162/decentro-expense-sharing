def setup_group_with_users(client):
    g_id = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    u1 = client.post("/users", json={"name": "Mohit"}).json()["id"]
    u2 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    u3 = client.post("/users", json={"name": "Ankit"}).json()["id"]

    for uid in [u1, u2, u3]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    return g_id, u1, u2, u3

def test_add_expense_equal_split_benchmark(client):
    """Tests the PDF example: Dinner = ₹1200 paid by Mohit among 3 members."""
    g_id, u1, u2, u3 = setup_group_with_users(client)

    exp_payload = {
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1200.0,
        "description": "Dinner",
        "category": "Food"
    }
    res = client.post("/expenses", json=exp_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["description"] == "Dinner"
    assert data["amount"] == 1200.0
    assert data["paid_by"] == "Mohit"
    assert len(data["splits"]) == 3
    for s in data["splits"]:
        assert s["amount"] == 400.0

def test_add_expense_custom_unequal_splits(client):
    """Tests the bonus feature: Unequal Expense Split."""
    g_id, u1, u2, u3 = setup_group_with_users(client)

    exp_payload = {
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1000.0,
        "description": "Custom lunch",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1, "amount": 500.0},
            {"user_id": u2, "amount": 300.0},
            {"user_id": u3, "amount": 200.0}
        ]
    }
    res = client.post("/expenses", json=exp_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["split_type"] == "EXACT"
    assert len(data["splits"]) == 3
    split_map = {s["user_name"]: s["amount"] for s in data["splits"]}
    assert split_map["Mohit"] == 500.0
    assert split_map["Rahul"] == 300.0
    assert split_map["Ankit"] == 200.0

def test_add_expense_validation_amount_negative(client):
    g_id, u1, _, _ = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": -50.0,
        "description": "Invalid expense"
    })
    assert res.status_code == 422

def test_add_expense_validation_non_member_payer(client):
    g_id, _, _, _ = setup_group_with_users(client)
    outsider_id = client.post("/users", json={"name": "Outsider"}).json()["id"]

    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": outsider_id,
        "amount": 500.0,
        "description": "Party"
    })
    assert res.status_code == 400
    assert "not a member" in res.json()["detail"]

def test_add_expense_custom_splits_mismatch(client):
    g_id, u1, u2, u3 = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1000.0,
        "description": "Bad math",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1, "amount": 400.0},
            {"user_id": u2, "amount": 300.0}  # total 700 != 1000
        ]
    })
    assert res.status_code == 422

def test_list_group_expenses_and_filters(client):
    g_id, u1, _, _ = setup_group_with_users(client)

    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1200.0,
        "description": "Dinner",
        "category": "Food"
    })
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 450.0,
        "description": "Taxi ride",
        "category": "Transport"
    })

    # List all
    res = client.get(f"/groups/{g_id}/expenses")
    assert res.status_code == 200
    assert len(res.json()) == 2

    # Filter by category
    res_food = client.get(f"/groups/{g_id}/expenses?category=Food")
    assert len(res_food.json()) == 1
    assert res_food.json()[0]["description"] == "Dinner"

    # Search filter
    res_search = client.get(f"/groups/{g_id}/expenses?search=taxi")
    assert len(res_search.json()) == 1
    assert res_search.json()[0]["description"] == "Taxi ride"
