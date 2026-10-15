from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserCreate, UserResponse
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Part 1 — Create User
    Example Request:
    { "name": "Mohit" }
    Example Response:
    { "id": 1, "name": "Mohit" }
    """
    return user_service.create_user(db, user_in)

@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """
    Part 1 — List Users
    Return all users in the system.
    """
    return user_service.list_users(db)
