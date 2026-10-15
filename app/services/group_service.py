from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Group, GroupMember, User
from app.schemas import GroupCreate

def create_group(db: Session, group_in: GroupCreate) -> Group:
    group = Group(name=group_in.name, description=group_in.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

def get_group_by_id(db: Session, group_id: int) -> Optional[Group]:
    return db.query(Group).filter(Group.id == group_id).first()

def list_groups(db: Session) -> List[Group]:
    return db.query(Group).order_by(Group.id.asc()).all()

def add_user_to_group(db: Session, group_id: int, user_id: int) -> GroupMember:
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {group_id} not found"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()

    if existing:
        return existing

    member = GroupMember(group_id=group_id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def list_group_members(db: Session, group_id: int) -> List[User]:
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {group_id} not found"
        )
    return [gm.user for gm in group.members]

def is_user_in_group(db: Session, group_id: int, user_id: int) -> bool:
    count = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).count()
    return count > 0
