from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SettlementCreate, SettlementResponse
from app.services import settlement_service

router = APIRouter(tags=["Settlements"])

@router.post("/settlements", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def create_settlement(settlement_in: SettlementCreate, db: Session = Depends(get_db)):
    """
    Optional Bonus Feature — Balance Settlement
    Record a payment between users to settle an existing balance.
    Example: Rahul pays Mohit 400.
    """
    settlement = settlement_service.record_settlement(db, settlement_in)
    return SettlementResponse(
        id=settlement.id,
        group_id=settlement.group_id,
        payer_id=settlement.payer_id,
        payer_name=settlement.payer.name if settlement.payer else str(settlement.payer_id),
        payee_id=settlement.payee_id,
        payee_name=settlement.payee.name if settlement.payee else str(settlement.payee_id),
        amount=settlement.amount,
        notes=settlement.notes,
        created_at=settlement.created_at
    )

@router.get("/groups/{group_id}/settlements", response_model=List[SettlementResponse])
def list_group_settlements(group_id: int, db: Session = Depends(get_db)):
    """List all settlements recorded in a group."""
    settlements = settlement_service.list_group_settlements(db, group_id)
    return [
        SettlementResponse(
            id=st.id,
            group_id=st.group_id,
            payer_id=st.payer_id,
            payer_name=st.payer.name if st.payer else str(st.payer_id),
            payee_id=st.payee_id,
            payee_name=st.payee.name if st.payee else str(st.payee_id),
            amount=st.amount,
            notes=st.notes,
            created_at=st.created_at
        )
        for st in settlements
    ]
