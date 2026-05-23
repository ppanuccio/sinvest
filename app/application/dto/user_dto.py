"""Data Transfer Objects for User-related operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# ============= Request DTOs =============

@dataclass
class CreateUserDTO:
    """DTO for creating a new user."""

    username: str
    email: str
    password: str


@dataclass
class GetUserDTO:
    """DTO for getting user details."""

    user_id: str


# ============= Response DTOs =============

@dataclass
class UserResponseDTO:
    """DTO returned when user is retrieved or created."""

    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
