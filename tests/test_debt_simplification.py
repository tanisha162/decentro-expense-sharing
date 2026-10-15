def setup_three_user_group(client):
    g_id = client.post("/groups", json={"name": "Road Trip"}).json()["id"]
    u1 = client.post("/users", json={"name": "Alice"}).json()["id"]
    u2 = client.post("/users", json={"name": "Bob"}).json()["id"]
    u3 = client.post("/users", json={"name": "Charlie"}).json()["id"]

    for uid in [u1, u2, u3]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    return g_id, u1, u2, u3

def test_debt_simplification_minimizes_transactions(client):
    """
    Scenario:
    - Alice pays 300 only for Bob (Bob owes Alice 300)
    - Bob pays 300 only for Charlie (Charlie owes Bob 300)
    Without simplification:
    - Bob pays Alice 300
    - Charlie pays Bob 300
    (2 transactions)
    With debt simplification:
    - Charlie's net is -300
    - Bob's net is 0
    - Alice's net is +300
    Result: Charlie pays Alice 300 directly (1 transaction)!
    """
    g_id, u1, u2, u3 = setup_three_user_group(client)

    # Alice pays 300 with exact split only for Bob
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 300.0,
        "description": "Lunch for Bob",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u2, "amount": 300.0}
        ]
    })

    # Bob pays 300 with exact split only for Charlie
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u2,
        "amount": 300.0,
        "description": "Ticket for Charlie",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u3, "amount": 300.0}
        ]
    })

    # Query group balance detail
    res = client.get(f"/groups/{g_id}/balances")
    assert res.status_code == 200
    data = res.json()

    # Net balances:
    net_bals = data["net_balances"]
    assert net_bals["Alice"] == 300.0
    assert net_bals["Bob"] == 0.0
    assert net_bals["Charlie"] == -300.0

    # Simplified debts should contain only 1 transaction: Charlie pays Alice 300!
    simplified = data["simplified_debts"]
    assert len(simplified) == 1
    assert simplified[0]["from_user_name"] == "Charlie"
    assert simplified[0]["to_user_name"] == "Alice"
    assert simplified[0]["amount"] == 300.0

def test_group_analytics_and_csv_export(client):
    g_id, u1, u2, u3 = setup_three_user_group(client)

    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 900.0,
        "description": "Hotel Stay",
        "category": "Stay",
        "split_type": "EQUAL"
    })

    # Analytics check
    analytics_res = client.get(f"/groups/{g_id}/analytics")
    assert analytics_res.status_code == 200
    an_data = analytics_res.json()
    assert an_data["total_spent"] == 900.0
    assert an_data["average_per_member"] == 300.0
    assert len(an_data["categories"]) == 1
    assert an_data["categories"][0]["category"] == "Stay"

    # CSV Export check
    csv_res = client.get(f"/groups/{g_id}/export?format=csv")
    assert csv_res.status_code == 200
    assert "Hotel Stay" in csv_res.text
    assert "text/csv" in csv_res.headers["content-type"]
