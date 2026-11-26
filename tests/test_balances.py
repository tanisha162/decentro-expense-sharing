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

def test_balances_for_unknown_group_returns_404(client):
    """
    GET /balances?group_id=<nonexistent> used to return 200 with {},
    indistinguishable from "group exists and nobody owes anything" —
    every other group-scoped endpoint 404s on an unknown group.
    """
    res = client.get("/balances?group_id=9999")
    assert res.status_code == 404

def test_duplicate_names_balances_aggregate(client):
    """
    Two members may share a display name. Balances are keyed by name, so
    their debts must be summed, not overwritten: two "Rahul"s each owing
    Mohit 300 must show as Rahul owing Mohit 600, with net -600.
    Previously the second entry overwrote the first (300 / -300), while
    the id-keyed simplified debts correctly totalled 600 — the same
    response contradicted itself.
    """
    g_id = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    r1 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    r2 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    mohit = client.post("/users", json={"name": "Mohit"}).json()["id"]

    for uid in [r1, r2, mohit]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": mohit,
        "amount": 900.0,
        "description": "Dinner"
    })

    res = client.get(f"/groups/{g_id}/balances")
    assert res.status_code == 200
    data = res.json()

    # Both Rahuls owe 300 each -> 600 total under the shared name
    assert data["balances"]["Rahul"]["owes"]["Mohit"] == 600.0
    assert data["net_balances"]["Rahul"] == -600.0
    assert data["net_balances"]["Mohit"] == 600.0
    # Name-keyed books must balance
    assert round(sum(data["net_balances"].values()), 2) == 0.0
    # Simplified debts (per user id) agree with the aggregated view
    rahul_debts = [d for d in data["simplified_debts"] if d["from_user_name"] == "Rahul"]
    assert len(rahul_debts) == 2
    assert sum(d["amount"] for d in rahul_debts) == 600.0

def test_duplicate_names_never_owe_themselves(client):
    """
    Two members sharing a name who owe *each other* must not render as
    "Rahul owes Rahul": the response is keyed by display name, so a debt
    between two Rahuls is internal to the Rahul bucket and its net effect
    on the bucket is zero. Only debts to a differently-named user show.
    """
    g_id = client.post("/groups", json={"name": "Goa Trip"}).json()["id"]
    r1 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    r2 = client.post("/users", json={"name": "Rahul"}).json()["id"]
    mohit = client.post("/users", json={"name": "Mohit"}).json()["id"]

    for uid in [r1, r2, mohit]:
        client.post(f"/groups/{g_id}/members", json={"user_id": uid})

    # Mohit pays 900: each Rahul owes Mohit 300.
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": mohit,
        "amount": 900.0,
        "description": "Dinner"
    })
    # Second Rahul pays 300: first Rahul now also owes second Rahul 100.
    client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": r2,
        "amount": 300.0,
        "description": "Breakfast"
    })

    res = client.get(f"/groups/{g_id}/balances")
    assert res.status_code == 200
    data = res.json()

    # The internal Rahul -> Rahul debt must not appear as a self-debt.
    assert "Rahul" not in data["balances"]["Rahul"]["owes"]
    # The real debts survive: Rahul#1 owes Mohit 300, Rahul#2 owes
    # Mohit 300 - 100 = 200, aggregated under the shared name.
    assert data["balances"]["Rahul"]["owes"]["Mohit"] == 500.0
    # Name-keyed books still balance.
    assert data["net_balances"]["Rahul"] == -500.0
    assert data["net_balances"]["Mohit"] == 500.0
    assert round(sum(data["net_balances"].values()), 2) == 0.0
