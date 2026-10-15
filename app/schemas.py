from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# ----------------- User Schemas -----------------
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User's display name")
    email: Optional[str] = Field(None, max_length=120, description="Optional email address")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Name cannot be empty or blank")
        return clean

class UserResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Group Schemas -----------------
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Group name cannot be empty or blank")
        return clean

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    members: Optional[List[UserResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class AddMemberRequest(BaseModel):
    group_id: Optional[int] = None
    user_id: int


# ----------------- Expense Split Schemas -----------------
class SplitItem(BaseModel):
    user_id: int
    amount: float = Field(..., ge=0, description="Specific amount this user owes")

class ExpenseSplitDetail(BaseModel):
    user_id: int
    user_name: str
    amount: float

    model_config = ConfigDict(from_attributes=True)


# ----------------- Expense Schemas -----------------
class ExpenseCreate(BaseModel):
    group_id: int
    paid_by: int
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    description: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field("General", max_length=50)
    split_type: Optional[str] = Field("EQUAL", description="EQUAL or EXACT")
    splits: Optional[List[SplitItem]] = Field(None, description="Custom unequal splits")

    @field_validator("description")
    @classmethod
    def desc_must_not_be_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Expense description cannot be empty")
        return clean

    @model_validator(mode="after")
    def validate_splits(self):
        if self.split_type == "EXACT":
            if not self.splits:
                raise ValueError("Splits list must be provided when split_type is EXACT")
            total_splits = sum(s.amount for s in self.splits)
            if abs(total_splits - self.amount) > 0.01:
                raise ValueError(
                    f"Sum of custom splits ({total_splits:.2f}) must equal the total expense amount ({self.amount:.2f})"
                )
        return self


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    description: str
    amount: float
    paid_by: str  # Required format from Page 7: name of the payer
    paid_by_id: int
    category: str
    split_type: str
    created_at: Optional[datetime] = None
    splits: Optional[List[ExpenseSplitDetail]] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Settlement Schemas -----------------
class SettlementCreate(BaseModel):
    group_id: int
    payer_id: int
    payee_id: int
    amount: float = Field(..., gt=0, description="Settlement amount must be > 0")
    notes: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_different_users(self):
        if self.payer_id == self.payee_id:
            raise ValueError("Payer and payee cannot be the same user")
        return self

class SettlementResponse(BaseModel):
    id: int
    group_id: int
    payer_id: int
    payer_name: str
    payee_id: int
    payee_name: str
    amount: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Balance & Analytics Schemas -----------------
class SimplifiedDebt(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: float

class GroupBalanceDetail(BaseModel):
    group_id: int
    group_name: str
    balances: Dict[str, Dict[str, Dict[str, float]]]
    net_balances: Dict[str, float]
    simplified_debts: List[SimplifiedDebt]
    total_group_spending: float

class CategorySpending(BaseModel):
    category: str
    total_amount: float
    percentage: float
    count: int

class UserSpendingSummary(BaseModel):
    user_id: int
    user_name: str
    total_paid: float
    total_share: float
    net_balance: float

class GroupAnalytics(BaseModel):
    group_id: int
    group_name: str
    total_spent: float
    expense_count: int
    member_count: int
    average_per_member: float
    categories: List[CategorySpending]
    user_summaries: List[UserSpendingSummary]
