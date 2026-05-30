from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: UserRole
    depot_id: Optional[int] = None
    full_name: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole
    depot_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    depot_id: Optional[int]
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str
