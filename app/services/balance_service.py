from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseSplit, Settlement, User, Group, GroupMember
from app.schemas import SimplifiedDebt, GroupBalanceDetail

def calculate_pairwise_balances_for_group(
    db: Session, group_id: int
) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, float], List[SimplifiedDebt], float]:
    """
    Calculates:
    1. Pairwise balances matching PDF Page 8 format:
       {
         "Rahul": {
           "owes": {
             "Mohit": 400
           }
         }
       }
    2. Net balances per user (positive = gets back, negative = owes).
    3. Simplified debts (Splitwise min-cash-flow algorithm).
    4. Total group spending.
    """
    # Load all members
    members = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id)
        .all()
    )
    user_map = {m.user.id: m.user for m in members}

    # Load all expenses for this group
    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group_id)
        .all()
    )

    # Load all settlements for this group
    settlements = (
        db.query(Settlement)
        .filter(Settlement.group_id == group_id)
        .all()
    )

    total_group_spending = sum(e.amount for e in expenses)

    # raw_debts[(debtor_id, creditor_id)] = amount
    raw_debts = defaultdict(float)

    # Net balance per user id
    net_balances_by_id = defaultdict(float)

    # 1. Process expenses
    for exp in expenses:
        payer_id = exp.paid_by
        # Ensure payer is in user map if possible
        if payer_id not in user_map:
            user_obj = db.query(User).filter(User.id == payer_id).first()
            if user_obj:
                user_map[payer_id] = user_obj

        for split in exp.splits:
            consumer_id = split.user_id
            if consumer_id not in user_map:
                user_obj = db.query(User).filter(User.id == consumer_id).first()
                if user_obj:
                    user_map[consumer_id] = user_obj

            share = split.amount

            # Rule: Payer should not owe themselves
            if consumer_id != payer_id:
                raw_debts[(consumer_id, payer_id)] += share

            # Update net balances:
            # Payer paid upfront (+)
            # Consumer consumed (-)
            # For the payer's own share, +share and -share cancel out to 0
            net_balances_by_id[consumer_id] -= share

        net_balances_by_id[payer_id] += exp.amount

    # 2. Process settlements (payer pays payee, reducing existing debt)
    for st in settlements:
        # Payer paid settlement -> their debt to payee decreases
        raw_debts[(st.payer_id, st.payee_id)] -= st.amount
        # In net terms: payer transferred money (+), payee received (-)
        net_balances_by_id[st.payer_id] += st.amount
        net_balances_by_id[st.payee_id] -= st.amount

    # 3. Calculate direct pairwise net debts
    # Compare raw_debts[(A, B)] and raw_debts[(B, A)]
    pairwise_balances: Dict[str, Dict[str, Dict[str, float]]] = {}
    processed_pairs = set()

    all_user_ids = list(user_map.keys())

    for i in range(len(all_user_ids)):
        for j in range(i + 1, len(all_user_ids)):
            u1 = all_user_ids[i]
            u2 = all_user_ids[j]

            u1_owes_u2 = raw_debts.get((u1, u2), 0.0)
            u2_owes_u1 = raw_debts.get((u2, u1), 0.0)

            diff = u1_owes_u2 - u2_owes_u1

            u1_name = user_map[u1].name if u1 in user_map else f"User {u1}"
            u2_name = user_map[u2].name if u2 in user_map else f"User {u2}"

            if diff > 0.005:
                # u1 owes u2
                amount = round(diff, 2)
                if u1_name not in pairwise_balances:
                    pairwise_balances[u1_name] = {"owes": {}}
                pairwise_balances[u1_name]["owes"][u2_name] = amount
            elif diff < -0.005:
                # u2 owes u1
                amount = round(-diff, 2)
                if u2_name not in pairwise_balances:
                    pairwise_balances[u2_name] = {"owes": {}}
                pairwise_balances[u2_name]["owes"][u1_name] = amount

    # 4. Formatted net balances (name -> net amount)
    formatted_net_balances: Dict[str, float] = {}
    for uid, net in net_balances_by_id.items():
        name = user_map[uid].name if uid in user_map else f"User {uid}"
        formatted_net_balances[name] = round(net, 2)

    # 5. Smart Debt Simplification Algorithm (Min-Cash-Flow)
    # Debtors: net < -0.005, Creditors: net > 0.005
    debtors: List[Tuple[int, float]] = []
    creditors: List[Tuple[int, float]] = []

    for uid, net in net_balances_by_id.items():
        if net < -0.005:
            debtors.append((uid, abs(net)))
        elif net > 0.005:
            creditors.append((uid, net))

    # Sort to greedily match largest debts first
    simplified_debts: List[SimplifiedDebt] = []

    # Using greedy matching
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor_id, debtor_amount = debtors[d_idx]
        creditor_id, creditor_amount = creditors[c_idx]

        settle_amt = min(debtor_amount, creditor_amount)
        if settle_amt > 0.005:
            d_name = user_map[debtor_id].name if debtor_id in user_map else f"User {debtor_id}"
            c_name = user_map[creditor_id].name if creditor_id in user_map else f"User {creditor_id}"
            
            simplified_debts.append(
                SimplifiedDebt(
                    from_user_id=debtor_id,
                    from_user_name=d_name,
                    to_user_id=creditor_id,
                    to_user_name=c_name,
                    amount=round(settle_amt, 2)
                )
            )

        new_d_amt = debtor_amount - settle_amt
        new_c_amt = creditor_amount - settle_amt

        if new_d_amt <= 0.005:
            d_idx += 1
        else:
            debtors[d_idx] = (debtor_id, new_d_amt)

        if new_c_amt <= 0.005:
            c_idx += 1
        else:
            creditors[c_idx] = (creditor_id, new_c_amt)

    return (
        pairwise_balances,
        formatted_net_balances,
        simplified_debts,
        round(total_group_spending, 2)
    )


def calculate_overall_balances(
    db: Session, group_id: Optional[int] = None
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Returns the exact required response schema for GET /balances:
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
    if group_id is not None:
        pairwise, _, _, _ = calculate_pairwise_balances_for_group(db, group_id)
        return pairwise

    # If no group_id, calculate across all groups
    groups = db.query(Group).all()
    overall: Dict[str, Dict[str, Dict[str, float]]] = {}

    for g in groups:
        pairwise, _, _, _ = calculate_pairwise_balances_for_group(db, g.id)
        for debtor, owes_dict in pairwise.items():
            if debtor not in overall:
                overall[debtor] = {"owes": {}}
            for creditor, amt in owes_dict.get("owes", {}).items():
                current = overall[debtor]["owes"].get(creditor, 0.0)
                overall[debtor]["owes"][creditor] = round(current + amt, 2)

    return overall
