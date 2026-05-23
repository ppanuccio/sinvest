"""Data Transfer Objects for Portfolio-related operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


# ============= Request DTOs =============

@dataclass
class CreatePortfolioDTO:
    """DTO for creating a new portfolio."""

    user_id: str
    name: str
    description: Optional[str] = None


@dataclass
class UpdatePortfolioDTO:
    """DTO for updating portfolio details."""

    name: Optional[str] = None
    description: Optional[str] = None


@dataclass
class GetPortfolioDTO:
    """DTO for retrieving a portfolio."""

    portfolio_id: str
    user_id: str


@dataclass
class ListPortfoliosDTO:
    """DTO for listing user portfolios."""

    user_id: str


# ============= Response DTOs =============

@dataclass
class PortfolioResponseDTO:
    """DTO returned for portfolio operations."""

    id: str
    user_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


@dataclass
class PortfolioDetailResponseDTO:
    """DTO for detailed portfolio view with investments."""

    id: str
    user_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    investment_count: int

    class Config:
        from_attributes = True
