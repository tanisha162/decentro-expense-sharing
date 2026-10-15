import csv
import io
from collections import defaultdict
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Group, Expense, ExpenseSplit, GroupMember, Settlement
from app.schemas import GroupAnalytics, CategorySpending, UserSpendingSummary
from app.services.balance_service import calculate_pairwise_balances_for_group

def get_group_analytics(db: Session, group_id: int) -> GroupAnalytics:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {group_id} not found"
        )

    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()

    total_spent = sum(e.amount for e in expenses)
    expense_count = len(expenses)
    member_count = len(members)
    avg_per_member = round(total_spent / member_count, 2) if member_count > 0 else 0.0

    # Category breakdown
    cat_totals = defaultdict(float)
    cat_counts = defaultdict(int)

    for e in expenses:
        cat = e.category or "General"
        cat_totals[cat] += e.amount
        cat_counts[cat] += 1

    categories = []
    for cat, total in cat_totals.items():
        pct = round((total / total_spent * 100.0), 2) if total_spent > 0 else 0.0
        categories.append(
            CategorySpending(
                category=cat,
                total_amount=round(total, 2),
                percentage=pct,
                count=cat_counts[cat]
            )
        )
    categories.sort(key=lambda x: x.total_amount, reverse=True)

    # Per-user summaries
    user_paid = defaultdict(float)
    user_shares = defaultdict(float)

    for e in expenses:
        user_paid[e.paid_by] += e.amount
        for s in e.splits:
            user_shares[s.user_id] += s.amount

    # Factor in settlements
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
    user_settled_paid = defaultdict(float)
    user_settled_received = defaultdict(float)

    for st in settlements:
        user_settled_paid[st.payer_id] += st.amount
        user_settled_received[st.payee_id] += st.amount

    user_summaries = []
    for m in members:
        u = m.user
        paid = user_paid.get(u.id, 0.0)
        share = user_shares.get(u.id, 0.0)
        st_paid = user_settled_paid.get(u.id, 0.0)
        st_recv = user_settled_received.get(u.id, 0.0)
        net = (paid + st_paid) - (share + st_recv)

        user_summaries.append(
            UserSpendingSummary(
                user_id=u.id,
                user_name=u.name,
                total_paid=round(paid, 2),
                total_share=round(share, 2),
                net_balance=round(net, 2)
            )
        )

    return GroupAnalytics(
        group_id=group.id,
        group_name=group.name,
        total_spent=round(total_spent, 2),
        expense_count=expense_count,
        member_count=member_count,
        average_per_member=avg_per_member,
        categories=categories,
        user_summaries=user_summaries
    )


def export_group_csv(db: Session, group_id: int) -> str:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).order_by(Expense.id.asc()).all()
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).order_by(Settlement.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Group info
    writer.writerow(["Group Expense Report", group.name])
    writer.writerow([])

    # 2. Expenses Section
    writer.writerow(["--- EXPENSES ---"])
    writer.writerow(["ID", "Description", "Category", "Amount (INR)", "Paid By", "Split Type", "Created At", "Splits Breakdown"])
    for exp in expenses:
        splits_str = "; ".join([f"{s.user.name}: {s.amount:.2f}" for s in exp.splits])
        writer.writerow([
            exp.id,
            exp.description,
            exp.category,
            f"{exp.amount:.2f}",
            exp.payer.name if exp.payer else exp.paid_by,
            exp.split_type,
            exp.created_at.strftime("%Y-%m-%d %H:%M:%S") if exp.created_at else "",
            splits_str
        ])

    writer.writerow([])
    # 3. Settlements Section
    writer.writerow(["--- SETTLEMENTS ---"])
    writer.writerow(["ID", "Payer", "Payee", "Amount (INR)", "Notes", "Date"])
    for st in settlements:
        writer.writerow([
            st.id,
            st.payer.name if st.payer else st.payer_id,
            st.payee.name if st.payee else st.payee_id,
            f"{st.amount:.2f}",
            st.notes or "",
            st.created_at.strftime("%Y-%m-%d %H:%M:%S") if st.created_at else ""
        ])

    writer.writerow([])
    # 4. Balances Section
    pairwise, net_bals, simplified, total_spending = calculate_pairwise_balances_for_group(db, group_id)
    writer.writerow(["--- OUTSTANDING BALANCES ---"])
    writer.writerow(["Debtor (Owes)", "Creditor (Gets)", "Amount (INR)"])
    for debtor, owes_dict in pairwise.items():
        for creditor, amt in owes_dict.get("owes", {}).items():
            writer.writerow([debtor, creditor, f"{amt:.2f}"])

    writer.writerow([])
    writer.writerow(["--- SMART SIMPLIFIED SETTLEMENTS ---"])
    writer.writerow(["From", "To", "Amount (INR)"])
    for s in simplified:
        writer.writerow([s.from_user_name, s.to_user_name, f"{s.amount:.2f}"])

    return output.getvalue()
