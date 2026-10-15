from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine
from app.models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement
from app.services import user_service, group_service, expense_service
from app.schemas import UserCreate, GroupCreate, ExpenseCreate

router = APIRouter(prefix="/api/demo", tags=["Demo & Utility"])

@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Seeds the standard Decentro Goa Trip scenario:
    - Users: Mohit, Rahul, Ankit
    - Group: Goa Trip
    - Expense: Dinner = 1200 paid by Mohit
    - Additional realistic expenses for richer UI/analytics demonstration.
    """
    # 1. Create or retrieve users
    users_data = ["Mohit", "Rahul", "Ankit", "Sneha"]
    user_objs = {}
    for name in users_data:
        existing = db.query(User).filter(User.name == name).first()
        if not existing:
            u = User(name=name, email=f"{name.lower()}@example.com")
            db.add(u)
            db.commit()
            db.refresh(u)
            user_objs[name] = u
        else:
            user_objs[name] = existing

    # 2. Create Goa Trip group
    group = db.query(Group).filter(Group.name == "Goa Trip").first()
    if not group:
        group = Group(name="Goa Trip", description="Annual friends trip to North Goa beaches")
        db.add(group)
        db.commit()
        db.refresh(group)

    # 3. Add Mohit, Rahul, Ankit to group
    for name in ["Mohit", "Rahul", "Ankit"]:
        u = user_objs[name]
        is_mem = db.query(GroupMember).filter(
            GroupMember.group_id == group.id,
            GroupMember.user_id == u.id
        ).first()
        if not is_mem:
            gm = GroupMember(group_id=group.id, user_id=u.id)
            db.add(gm)
    db.commit()

    # 4. Add the PDF benchmark expense: Dinner = ₹1200 paid by Mohit
    existing_dinner = db.query(Expense).filter(
        Expense.group_id == group.id,
        Expense.description == "Dinner"
    ).first()

    if not existing_dinner:
        expense_service.create_expense(
            db,
            ExpenseCreate(
                group_id=group.id,
                paid_by=user_objs["Mohit"].id,
                amount=1200.0,
                description="Dinner",
                category="Food",
                split_type="EQUAL"
            )
        )

        # Add a couple more expenses to showcase analytics and debt simplification
        expense_service.create_expense(
            db,
            ExpenseCreate(
                group_id=group.id,
                paid_by=user_objs["Rahul"].id,
                amount=600.0,
                description="Beach Shack Breakfast",
                category="Food",
                split_type="EQUAL"
            )
        )

        expense_service.create_expense(
            db,
            ExpenseCreate(
                group_id=group.id,
                paid_by=user_objs["Ankit"].id,
                amount=900.0,
                description="Airport Taxi",
                category="Transport",
                split_type="EQUAL"
            )
        )

    return {
        "status": "success",
        "message": "Demo data successfully seeded for 'Goa Trip'",
        "group_id": group.id,
        "users": [u.name for u in user_objs.values()]
    }


@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    """Deletes all data in the database for clean testing."""
    db.query(ExpenseSplit).delete()
    db.query(Expense).delete()
    db.query(Settlement).delete()
    db.query(GroupMember).delete()
    db.query(Group).delete()
    db.query(User).delete()
    db.commit()
    return {"status": "success", "message": "Database successfully cleared"}
