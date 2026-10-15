from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Settlement, Group, User, GroupMember
from app.schemas import SettlementCreate

def record_settlement(db: Session, settlement_in: SettlementCreate) -> Settlement:
    if settlement_in.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Settlement amount must be greater than 0"
        )

    if settlement_in.payer_id == settlement_in.payee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payer and payee cannot be the same user"
        )

    # Validate group exists
    group = db.query(Group).filter(Group.id == settlement_in.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {settlement_in.group_id} not found"
        )

    # Validate payer exists and is a member of the group
    payer = db.query(User).filter(User.id == settlement_in.payer_id).first()
    if not payer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payer user with id {settlement_in.payer_id} not found"
        )

    payer_member = db.query(GroupMember).filter(
        GroupMember.group_id == settlement_in.group_id,
        GroupMember.user_id == settlement_in.payer_id
    ).first()
    if not payer_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payer '{payer.name}' is not a member of group '{group.name}'"
        )

    # Validate payee exists and is a member of the group
    payee = db.query(User).filter(User.id == settlement_in.payee_id).first()
    if not payee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payee user with id {settlement_in.payee_id} not found"
        )

    payee_member = db.query(GroupMember).filter(
        GroupMember.group_id == settlement_in.group_id,
        GroupMember.user_id == settlement_in.payee_id
    ).first()
    if not payee_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payee '{payee.name}' is not a member of group '{group.name}'"
        )

    settlement = Settlement(
        group_id=settlement_in.group_id,
        payer_id=settlement_in.payer_id,
        payee_id=settlement_in.payee_id,
        amount=round(settlement_in.amount, 2),
        notes=settlement_in.notes
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement

def list_group_settlements(db: Session, group_id: int) -> List[Settlement]:
    return (
        db.query(Settlement)
        .filter(Settlement.group_id == group_id)
        .order_by(Settlement.created_at.desc())
        .all()
    )
