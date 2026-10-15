def setup_benchmark_group(client):
    g_id = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    u1 = client.post("/users", json={"name": "Mohit"}).json()["id"]
    u2 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    u3 = client.post("/users", json={"name": "Ankit"}).json()["id"]

    for uid in [u1, u2, u3]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    return g_id, u1, u2, u3

def test_benchmark_balance_calculation_exact_spec(client):
    """
    Directly tests the assignment requirement:
    Dinner = 1200 paid by Mohit among Mohit, Rahul, Ankit.
    Expects GET /balances:
    {
      "Rahul": {
        "owes": {
          "Mohit": 400
        }
      },
      "Ankit": {
        "owes": {
          "Mohit": 400
        }
      }
    }
    """
    g_id, u1, u2, u3 = setup_benchmark_group(client)

    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1200.0,
        "description": "Dinner"
    })

    res = client.get("/balances")
    assert res.status_code == 200
    balances = res.json()

    # Mohit should not owe anyone
    assert "Mohit" not in balances

    # Rahul owes Mohit 400
    assert "Rahul" in balances
    assert balances["Rahul"]["owes"]["Mohit"] == 400.0

    # Ankit owes Mohit 400
    assert "Ankit" in balances
    assert balances["Ankit"]["owes"]["Mohit"] == 400.0

def test_bidirectional_expense_netting(client):
    """
    1. Dinner = 1200 paid by Mohit (Rahul owes Mohit 400, Ankit owes Mohit 400).
    2. Breakfast = 600 paid by Rahul (Mohit owes Rahul 200, Ankit owes Rahul 200).
    Net:
    - Rahul owes Mohit: 400 - 200 = 200.
    - Ankit owes Mohit: 400.
    - Ankit owes Rahul: 200.
    """
    g_id, u1, u2, u3 = setup_benchmark_group(client)

    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 1200.0,
        "description": "Dinner"
    })
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u2,
        "amount": 600.0,
        "description": "Breakfast"
    })

    res = client.get("/balances")
    balances = res.json()

    assert balances["Rahul"]["owes"]["Mohit"] == 200.0
    assert balances["Ankit"]["owes"]["Mohit"] == 400.0
    assert balances["Ankit"]["owes"]["Rahul"] == 200.0
