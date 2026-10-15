from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseSplit, Group, User, GroupMember
from app.schemas import ExpenseCreate, ExpenseResponse, ExpenseSplitDetail

def create_expense(db: Session, expense_in: ExpenseCreate) -> Expense:
    # 1. Validate amount
    if expense_in.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense amount must be greater than 0"
        )

    # 2. Validate group exists
    group = db.query(Group).filter(Group.id == expense_in.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {expense_in.group_id} not found"
        )

    # 3. Validate group has members
    members = db.query(GroupMember).filter(GroupMember.group_id == expense_in.group_id).all()
    if not members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add expense to an empty group. Add members to the group first."
        )

    member_user_ids = {m.user_id for m in members}

    # 4. Validate payer exists and is in the group
    payer = db.query(User).filter(User.id == expense_in.paid_by).first()
    if not payer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payer user with id {expense_in.paid_by} not found"
        )

    if expense_in.paid_by not in member_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payer '{payer.name}' (id: {expense_in.paid_by}) is not a member of group '{group.name}'"
        )

    # 5. Create Expense record
    category = expense_in.category or "General"
    split_type = expense_in.split_type or "EQUAL"

    expense = Expense(
        group_id=expense_in.group_id,
        paid_by=expense_in.paid_by,
        amount=round(expense_in.amount, 2),
        description=expense_in.description.strip(),
        category=category,
        split_type=split_type
    )
    db.add(expense)
    db.flush()  # populate expense.id

    # 6. Calculate splits
    splits_to_create = []

    if split_type == "EXACT":
        if not expense_in.splits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom splits required when split_type is 'EXACT'"
            )
        
        # Validate all split users are group members
        split_total = 0.0
        seen_users = set()
        for item in expense_in.splits:
            if item.user_id in seen_users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate user_id {item.user_id} in splits list"
                )
            seen_users.add(item.user_id)

            if item.user_id not in member_user_ids:
                user_obj = db.query(User).filter(User.id == item.user_id).first()
                u_name = user_obj.name if user_obj else str(item.user_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User '{u_name}' in splits is not a member of group '{group.name}'"
                )
            
            splits_to_create.append(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=item.user_id,
                    amount=round(item.amount, 2)
                )
            )
            split_total += item.amount

        if abs(split_total - expense_in.amount) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of custom splits ({split_total:.2f}) does not match expense amount ({expense_in.amount:.2f})"
            )
    else:
        # EQUAL split among all members of the group
        num_members = len(member_user_ids)
        total_cents = int(round(expense_in.amount * 100))
        base_cents_each = total_cents // num_members
        remainder_cents = total_cents % num_members

        sorted_member_ids = sorted(list(member_user_ids))
        for idx, u_id in enumerate(sorted_member_ids):
            # Distribute remainder cents to first few participants for exact precision
            cents = base_cents_each + (1 if idx < remainder_cents else 0)
            share_amount = cents / 100.0
            splits_to_create.append(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=u_id,
                    amount=share_amount
                )
            )

    db.add_all(splits_to_create)
    db.commit()
    db.refresh(expense)
    return expense


def list_group_expenses(
    db: Session,
    group_id: int,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> List[Expense]:
    # Validate group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {group_id} not found"
        )

    query = db.query(Expense).filter(Expense.group_id == group_id)

    if category and category.lower() != "all":
        query = query.filter(Expense.category.ilike(category))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(Expense.description.ilike(term))

    return query.order_by(Expense.created_at.desc(), Expense.id.desc()).all()


def format_expense_response(expense: Expense) -> dict:
    """Formats an Expense model instance into the required response schema."""
    split_details = [
        ExpenseSplitDetail(
            user_id=s.user_id,
            user_name=s.user.name if s.user else f"User {s.user_id}",
            amount=s.amount
        )
        for s in expense.splits
    ]
    return {
        "id": expense.id,
        "group_id": expense.group_id,
        "description": expense.description,
        "amount": expense.amount,
        "paid_by": expense.payer.name if expense.payer else str(expense.paid_by),
        "paid_by_id": expense.paid_by,
        "category": expense.category,
        "split_type": expense.split_type,
        "created_at": expense.created_at,
        "splits": split_details
    }
