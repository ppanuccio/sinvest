"""Data Transfer Objects for authentication operations."""

from dataclasses import dataclass


@dataclass
class LoginDTO:
    """DTO for login credentials."""

    username: str
    password: str


@dataclass
class AuthTokenDTO:
    """DTO returned after successful authentication."""

    access_token: str
    token_type: str
    user_id: str
    username: str
