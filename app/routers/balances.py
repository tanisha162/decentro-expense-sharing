from typing import Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import balance_service

router = APIRouter(tags=["Balances"])

@router.get("/balances", response_model=Dict[str, Dict[str, Dict[str, float]]])
def get_balances(
    group_id: Optional[int] = Query(None, description="Optional group_id to filter balances for a specific group"),
    db: Session = Depends(get_db)
):
    """
    Part 4 — Balance Calculation
    Provide an API that returns balances in a structured format.
    Example Response:
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
    return balance_service.calculate_overall_balances(db, group_id=group_id)
