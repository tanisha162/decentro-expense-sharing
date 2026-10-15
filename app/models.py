from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    group_memberships = relationship(
        "GroupMember", back_populates="user", cascade="all, delete-orphan"
    )
    expenses_paid = relationship(
        "Expense", back_populates="payer", foreign_keys="Expense.paid_by"
    )
    expense_splits = relationship(
        "ExpenseSplit", back_populates="user", cascade="all, delete-orphan"
    )
    settlements_paid = relationship(
        "Settlement", back_populates="payer", foreign_keys="Settlement.payer_id"
    )
    settlements_received = relationship(
        "Settlement", back_populates="payee", foreign_keys="Settlement.payee_id"
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    members = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    expenses = relationship(
        "Expense", back_populates="group", cascade="all, delete-orphan"
    )
    settlements = relationship(
        "Settlement", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(50), default="General", nullable=False)
    split_type = Column(String(20), default="EQUAL", nullable=False)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_expense_amount_positive"),
    )

    # Relationships
    group = relationship("Group", back_populates="expenses")
    payer = relationship("User", back_populates="expenses_paid", foreign_keys=[paid_by])
    splits = relationship(
        "ExpenseSplit", back_populates="expense", cascade="all, delete-orphan"
    )


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_user"),
        CheckConstraint("amount >= 0", name="chk_split_amount_non_negative"),
    )

    # Relationships
    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", back_populates="expense_splits")


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_settlement_amount_positive"),
        CheckConstraint("payer_id != payee_id", name="chk_settlement_different_users"),
    )

    # Relationships
    group = relationship("Group", back_populates="settlements")
    payer = relationship("User", back_populates="settlements_paid", foreign_keys=[payer_id])
    payee = relationship("User", back_populates="settlements_received", foreign_keys=[payee_id])
