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

def test_add_expense_exact_splits_rounding_balances(client):
    """Sub-cent EXACT splits must still sum to the expense amount: splits of
    33.333 / 33.333 / 33.334 for a 100.00 expense used to be stored as
    33.33 x 3 = 99.99, leaving a phantom cent in the net balances."""
    g_id, u1, u2, u3 = setup_group_with_users(client)

    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 100.0,
        "description": "Thirds",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1, "amount": 33.333},
            {"user_id": u2, "amount": 33.333},
            {"user_id": u3, "amount": 33.334},
        ],
    })
    assert res.status_code == 201
    data = res.json()
    assert round(sum(s["amount"] for s in data["splits"]), 2) == 100.0

    # The ledger must balance: net balances sum to zero.
    bals = client.get(f"/groups/{g_id}/balances").json()
    assert round(sum(bals["net_balances"].values()), 2) == 0.0

def test_add_expense_rejected_exact_splits_store_nothing(client):
    """A rejected EXACT expense must store nothing. The split validation
    used to run after the expense was added and flushed, so a 400 for a
    duplicate user or a non-member in the splits left the expense row
    behind: it showed up in the expense list and credited the payer
    ₹100 with no matching shares, so net balances summed to +100."""
    g_id, u1, u2, u3 = setup_group_with_users(client)
    outsider = client.post("/users", json={"name": "Outsider"}).json()["id"]

    # Duplicate user in splits
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 100.0,
        "description": "Dup split",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1, "amount": 50.0},
            {"user_id": u1, "amount": 50.0},
        ],
    })
    assert res.status_code == 400
    assert client.get(f"/groups/{g_id}/expenses").json() == []

    # Non-member in splits
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 100.0,
        "description": "Outsider split",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1, "amount": 50.0},
            {"user_id": outsider, "amount": 50.0},
        ],
    })
    assert res.status_code == 400
    assert client.get(f"/groups/{g_id}/expenses").json() == []

    # The ledger is untouched: no spending, balances sum to zero.
    bals = client.get(f"/groups/{g_id}/balances").json()
    assert bals["total_group_spending"] == 0.0
    assert bals["net_balances"] == {}

def test_add_expense_equal_with_splits_rejected(client):
    """Custom splits with split_type EQUAL must be rejected, not silently
    discarded while the expense is stored as an equal split (regression:
    splits [{Rahul: 90}] on a 100.00 EQUAL expense returned 201 with
    33.34/33.33/33.33 equal splits). An empty splits list stays accepted."""
    g_id, u1, u2, _ = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 100.0,
        "description": "Ignored splits",
        "split_type": "EQUAL",
        "splits": [{"user_id": u2, "amount": 90.0}],
    })
    assert res.status_code == 422
    # Nothing was stored for the rejected expense
    assert client.get(f"/groups/{g_id}/expenses").json() == []

    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 90.0,
        "description": "Empty splits list",
        "split_type": "EQUAL",
        "splits": [],
    })
    assert res.status_code == 201
    assert len(res.json()["splits"]) == 3

def test_add_expense_validation_amount_negative(client):
    g_id, u1, _, _ = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": -50.0,
        "description": "Invalid expense"
    })
    assert res.status_code == 422

def test_add_expense_invalid_split_type_rejected(client):
    """Unknown split_type must be rejected, not stored while splits are
    silently computed as EQUAL (regression: 'PERCENTAGE' returned 201)."""
    g_id, u1, _, _ = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 900.0,
        "description": "Bogus split type",
        "split_type": "PERCENTAGE"
    })
    assert res.status_code == 422
    # Nothing was stored for the rejected expense
    assert client.get(f"/groups/{g_id}/expenses").json() == []

def test_add_expense_split_type_case_normalized(client):
    """Lowercase split_type is accepted but stored canonical uppercase."""
    g_id, u1, _, _ = setup_group_with_users(client)
    res = client.post("/expenses", json={
        "group_id": g_id,
        "paid_by": u1,
        "amount": 900.0,
        "description": "Lowercase equal",
        "split_type": "equal"
    })
    assert res.status_code == 201
    assert res.json()["split_type"] == "EQUAL"
    assert len(res.json()["splits"]) == 3

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

def test_expense_category_is_stripped_and_blank_becomes_general(client):
    """A category with surrounding whitespace used to be stored verbatim,
    so " Food " and "Food" landed in separate analytics buckets and the
    ?category=Food filter missed the padded expense; a whitespace-only
    category became its own bucket instead of "General"."""
    g_id, u1, u2, u3 = setup_group_with_users(client)

    res = client.post("/expenses", json={
        "group_id": g_id, "paid_by": u1, "amount": 100.0,
        "description": "Lunch", "category": " Food "
    })
    assert res.status_code == 201
    assert res.json()["category"] == "Food"

    res = client.post("/expenses", json={
        "group_id": g_id, "paid_by": u1, "amount": 50.0,
        "description": "Snacks", "category": "Food"
    })
    assert res.status_code == 201

    res = client.post("/expenses", json={
        "group_id": g_id, "paid_by": u1, "amount": 10.0,
        "description": "Misc", "category": "   "
    })
    assert res.status_code == 201
    assert res.json()["category"] == "General"

    # One bucket for Food, found by the category filter
    an = client.get(f"/groups/{g_id}/analytics").json()
    food_buckets = [c for c in an["categories"] if c["category"] == "Food"]
    assert len(food_buckets) == 1
    assert food_buckets[0]["total_amount"] == 150.0
    assert food_buckets[0]["count"] == 2

    res_food = client.get(f"/groups/{g_id}/expenses?category=Food")
    assert len(res_food.json()) == 2

def test_expense_category_case_is_normalized(client):
    """Categories differing only in case ("food", "FOOD", "Food") used to
    be stored verbatim, so analytics split one logical category into
    three separate buckets instead of one."""
    g_id, u1, u2, u3 = setup_group_with_users(client)

    for cat in ("food", "FOOD", "Food"):
        res = client.post("/expenses", json={
            "group_id": g_id, "paid_by": u1, "amount": 100.0,
            "description": f"Meal {cat}", "category": cat
        })
        assert res.status_code == 201
        assert res.json()["category"] == "Food"

    # One bucket for Food totalling all three expenses
    an = client.get(f"/groups/{g_id}/analytics").json()
    food_buckets = [c for c in an["categories"] if c["category"] == "Food"]
    assert len(food_buckets) == 1
    assert food_buckets[0]["total_amount"] == 300.0
    assert food_buckets[0]["count"] == 3
