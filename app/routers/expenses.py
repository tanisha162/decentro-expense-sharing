from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ExpenseCreate, ExpenseResponse
from app.services import expense_service

router = APIRouter(tags=["Expenses"])

@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def add_expense(expense_in: ExpenseCreate, db: Session = Depends(get_db)):
    """
    Part 3 — Add Expense
    Example Request:
    {
      "group_id": 1,
      "paid_by": 1,
      "amount": 1200,
      "description": "Dinner"
    }
    """
    expense = expense_service.create_expense(db, expense_in)
    return expense_service.format_expense_response(expense)

@router.get("/groups/{group_id}/expenses", response_model=List[ExpenseResponse])
def list_group_expenses(
    group_id: int,
    category: Optional[str] = Query(None, description="Filter by category (Food, Transport, Stay, Activities, etc.)"),
    search: Optional[str] = Query(None, description="Search by keyword in description"),
    db: Session = Depends(get_db)
):
    """
    Part 3 — List Expenses
    Return all expenses for a particular group.
    Example Response:
    [
      {
        "description": "Dinner",
        "amount": 1200,
        "paid_by": "Mohit"
      }
    ]
    """
    expenses = expense_service.list_group_expenses(db, group_id, category, search)
    return [expense_service.format_expense_response(e) for e in expenses]

@router.get("/expenses", response_model=List[ExpenseResponse])
def list_expenses_query(
    group_id: Optional[int] = Query(None, description="Group ID to list expenses for"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by description"),
    db: Session = Depends(get_db)
):
    """Convenience endpoint to query expenses with query parameters."""
    if group_id is not None:
        expenses = expense_service.list_group_expenses(db, group_id, category, search)
    else:
        # All expenses
        from app.models import Expense
        query = db.query(Expense)
        if category and category.lower() != "all":
            query = query.filter(Expense.category.ilike(category))
        if search and search.strip():
            query = query.filter(Expense.description.ilike(f"%{search.strip()}%"))
        expenses = query.order_by(Expense.created_at.desc(), Expense.id.desc()).all()

    return [expense_service.format_expense_response(e) for e in expenses]
