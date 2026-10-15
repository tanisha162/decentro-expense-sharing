from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    GroupCreate, GroupResponse, UserResponse, AddMemberRequest,
    GroupBalanceDetail, GroupAnalytics
)
from app.services import group_service, balance_service, analytics_service

router = APIRouter(prefix="/groups", tags=["Groups"])

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group_in: GroupCreate, db: Session = Depends(get_db)):
    """
    Part 2 — Create Group
    Example Request:
    { "name": "Goa Trip" }
    Example Response:
    { "id": 1, "name": "Goa Trip" }
    """
    return group_service.create_group(db, group_in)

@router.get("", response_model=List[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    """List all groups."""
    groups = group_service.list_groups(db)
    result = []
    for g in groups:
        members = [gm.user for gm in g.members]
        result.append(
            GroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                created_at=g.created_at,
                members=members
            )
        )
    return result

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """Get group details including members."""
    group = group_service.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    members = [gm.user for gm in group.members]
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        members=members
    )

@router.post("/{group_id}/members", status_code=status.HTTP_200_OK)
def add_user_to_group(group_id: int, member_in: AddMemberRequest, db: Session = Depends(get_db)):
    """
    Part 2 — Add User To Group
    Path: /groups/{group_id}/members
    Example Request:
    { "group_id": 1, "user_id": 2 } or { "user_id": 2 }
    """
    target_group_id = member_in.group_id or group_id
    member = group_service.add_user_to_group(db, target_group_id, member_in.user_id)
    return {
        "message": f"User {member.user.name} added to group {member.group.name}",
        "group_id": member.group_id,
        "user_id": member.user_id,
        "user_name": member.user.name
    }

@router.get("/{group_id}/members", response_model=List[UserResponse])
def list_group_members(group_id: int, db: Session = Depends(get_db)):
    """
    Part 2 — List Group Members
    Return all members belonging to a group.
    """
    return group_service.list_group_members(db, group_id)

@router.get("/{group_id}/balances", response_model=GroupBalanceDetail)
def get_group_balances(group_id: int, db: Session = Depends(get_db)):
    """
    Returns detailed group balances, pairwise debts, net user balances,
    and smart debt simplification settlements.
    """
    group = group_service.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    pairwise, net_bals, simplified, total_spending = balance_service.calculate_pairwise_balances_for_group(db, group_id)
    return GroupBalanceDetail(
        group_id=group.id,
        group_name=group.name,
        balances=pairwise,
        net_balances=net_bals,
        simplified_debts=simplified,
        total_group_spending=total_spending
    )

@router.get("/{group_id}/analytics", response_model=GroupAnalytics)
def get_group_analytics(group_id: int, db: Session = Depends(get_db)):
    """
    Product Enhancement: Spending analytics, category breakdown, and member metrics.
    """
    return analytics_service.get_group_analytics(db, group_id)

@router.get("/{group_id}/export")
def export_group_data(group_id: int, format: str = "csv", db: Session = Depends(get_db)):
    """
    Product Enhancement: Export expenses, settlements, and balances to CSV or JSON.
    """
    if format.lower() == "csv":
        csv_data = analytics_service.export_group_csv(db, group_id)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=group_{group_id}_report.csv"}
        )
    elif format.lower() == "json":
        analytics = analytics_service.get_group_analytics(db, group_id)
        pairwise, net_bals, simplified, _ = balance_service.calculate_pairwise_balances_for_group(db, group_id)
        return {
            "analytics": analytics.model_dump(),
            "pairwise_balances": pairwise,
            "net_balances": net_bals,
            "simplified_settlements": [s.model_dump() for s in simplified]
        }
    else:
        raise HTTPException(status_code=400, detail="Supported export formats: 'csv', 'json'")
