"""User use cases - orchestrates user-related domain operations."""

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.validation_service import ValidationService
from app.domain.exceptions import DuplicateUserException, EntityNotFoundException
from app.application.dto.user_dto import (
    CreateUserDTO,
    UserResponseDTO,
)
import uuid
from datetime import datetime


class UserUseCases:
    """Orchestrates all user-related operations."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.validation_service = ValidationService()

    def create_user(self, dto: CreateUserDTO) -> UserResponseDTO:
        """
        Create a new user.
        Raises DuplicateUserException if username already exists.
        """
        # Validate input
        self.validation_service.validate_username(dto.username)
        self.validation_service.validate_email(dto.email)

        # Check if user already exists
        if self.user_repository.exists_by_username(dto.username):
            raise DuplicateUserException(dto.username)

        # Create user entity
        user = User(
            id=str(uuid.uuid4()),
            username=dto.username,
            email=dto.email,
            created_at=datetime.utcnow(),
        )

        # Save and return
        saved_user = self.user_repository.save(user)
        return UserResponseDTO(
            id=saved_user.id,
            username=saved_user.username,
            email=saved_user.email,
            created_at=saved_user.created_at,
            updated_at=saved_user.updated_at,
        )

    def get_user(self, user_id: str) -> UserResponseDTO:
        """Get user by ID. Raises EntityNotFoundException if not found."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        return UserResponseDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_user_by_username(self, username: str) -> UserResponseDTO:
        """Get user by username. Raises EntityNotFoundException if not found."""
        user = self.user_repository.get_by_username(username)
        if not user:
            raise EntityNotFoundException("User", username)

        return UserResponseDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def user_exists(self, username: str) -> bool:
        """Check if user with given username exists."""
        return self.user_repository.exists_by_username(username)
