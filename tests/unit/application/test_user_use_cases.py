"""Tests for user use cases."""

import pytest
from datetime import datetime

from app.application.use_cases.user_use_cases import UserUseCases
from app.application.dto.user_dto import CreateUserDTO
from app.domain.exceptions import DuplicateUserException, EntityNotFoundException
from tests.infrastructure.in_memory_repositories import InMemoryUserRepository


class TestUserUseCases:
    """Test user use cases."""

    @pytest.fixture
    def user_repo(self):
        return InMemoryUserRepository()

    @pytest.fixture
    def use_cases(self, user_repo):
        return UserUseCases(user_repo)

    def test_create_user_success(self, use_cases):
        """Test creating a new user."""
        dto = CreateUserDTO(
            username="john_doe",
            email="john@example.com",
            password="password123",
        )
        result = use_cases.create_user(dto)

        assert result.username == "john_doe"
        assert result.email == "john@example.com"
        assert result.id is not None
        assert result.created_at is not None

    def test_create_duplicate_user_fails(self, use_cases):
        """Test that duplicate username fails."""
        dto1 = CreateUserDTO(
            username="john_doe",
            email="john@example.com",
            password="password123",
        )
        use_cases.create_user(dto1)

        dto2 = CreateUserDTO(
            username="john_doe",
            email="different@example.com",
            password="password123",
        )
        with pytest.raises(DuplicateUserException):
            use_cases.create_user(dto2)

    def test_create_user_invalid_username(self, use_cases):
        """Test that short username fails."""
        dto = CreateUserDTO(
            username="ab",
            email="ab@example.com",
            password="password123",
        )
        with pytest.raises(ValueError):
            use_cases.create_user(dto)

    def test_create_user_invalid_email(self, use_cases):
        """Test that invalid email fails."""
        dto = CreateUserDTO(
            username="john_doe",
            email="invalid-email",
            password="password123",
        )
        with pytest.raises(ValueError):
            use_cases.create_user(dto)

    def test_get_user_exists(self, use_cases):
        """Test getting an existing user."""
        create_dto = CreateUserDTO(
            username="john_doe",
            email="john@example.com",
            password="password123",
        )
        created = use_cases.create_user(create_dto)

        result = use_cases.get_user(created.id)
        assert result.id == created.id
        assert result.username == "john_doe"

    def test_get_user_not_found(self, use_cases):
        """Test getting a non-existent user."""
        with pytest.raises(EntityNotFoundException):
            use_cases.get_user("non-existent-id")

    def test_get_user_by_username(self, use_cases):
        """Test getting user by username."""
        create_dto = CreateUserDTO(
            username="john_doe",
            email="john@example.com",
            password="password123",
        )
        created = use_cases.create_user(create_dto)

        result = use_cases.get_user_by_username("john_doe")
        assert result.id == created.id

    def test_user_exists(self, use_cases):
        """Test checking if user exists."""
        create_dto = CreateUserDTO(
            username="john_doe",
            email="john@example.com",
            password="password123",
        )
        use_cases.create_user(create_dto)

        assert use_cases.user_exists("john_doe")
        assert not use_cases.user_exists("non_existent")
