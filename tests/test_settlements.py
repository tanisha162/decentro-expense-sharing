def setup_benchmark_group(client):
    g_id = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    u1 = client.post("/users", json={"name": "Mohit"}).json()["id"]
    u2 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    u3 = client.post("/users", json={"name": "Ankit"}).json()["id"]

    for uid in [u1, u2, u3]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    return g_id, u1, u2, u3

def test_balance_settlement_bonus_spec(client):
    """
    Tests Bonus Feature:
    Dinner = 1200 paid by Mohit.
    Rahul owes Mohit 400.
    Rahul pays Mohit 400 (settlement).
    Updated Balance: Rahul owes Mohit 0.
    """
    g_id, u1, u2, u3 = setup_benchmark_group(client)

    # 1. Create expense
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1200.0,
        "description": "Dinner"
    })

    # Initial balance check
    initial_balances = client.get("/balances").json()
    assert initial_balances["Rahul"]["owes"]["Mohit"] == 400.0

    # 2. Record Settlement: Rahul (u2) pays Mohit (u1) 400
    st_res = client.post("/settlements", json={
        "group_id": g_id,
        "payer_id": u2,
        "payee_id": u1,
        "amount": 400.0,
        "notes": "Paid via Google Pay"
    })
    assert st_res.status_code == 201

    # 3. Check updated balance
    updated_balances = client.get("/balances").json()
    # Rahul now owes Mohit 0 (so Rahul does not owe Mohit)
    rahul_owes = updated_balances.get("Rahul", {}).get("owes", {})
    assert "Mohit" not in rahul_owes

    # Ankit still owes Mohit 400
    assert updated_balances["Ankit"]["owes"]["Mohit"] == 400.0

def test_settlement_validations(client):
    g_id, u1, u2, _ = setup_benchmark_group(client)

    # Same user validation
    res_same = client.post("/settlements", json={
        "group_id": g_id,
        "payer_id": u1,
        "payee_id": u1,
        "amount": 100.0
    })
    assert res_same.status_code == 422

    # Negative amount validation
    res_neg = client.post("/settlements", json={
        "group_id": g_id,
        "payer_id": u1,
        "payee_id": u2,
        "amount": -50.0
    })
    assert res_neg.status_code == 422
