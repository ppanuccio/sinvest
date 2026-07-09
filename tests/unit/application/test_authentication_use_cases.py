"""Tests for authentication use cases."""

import pytest

from app.application.dto.auth_dto import LoginDTO
from app.application.dto.user_dto import CreateUserDTO
from app.application.use_cases.authentication_use_cases import (
    AuthenticationUseCases,
)
from app.application.use_cases.user_use_cases import UserUseCases
from app.domain.exceptions import AuthenticationFailedException
from app.infrastructure.security import HMACTokenService, PBKDF2PasswordHasher
from tests.infrastructure.in_memory_repositories import (
    InMemoryCredentialRepository,
    InMemoryUserRepository,
)


class TestAuthenticationUseCases:
    """Test authentication use cases."""

    @pytest.fixture
    def user_repo(self):
        return InMemoryUserRepository()

    @pytest.fixture
    def credential_repo(self):
        return InMemoryCredentialRepository()

    @pytest.fixture
    def use_cases(self, user_repo, credential_repo):
        user_use_cases = UserUseCases(user_repo)
        return AuthenticationUseCases(
            user_use_cases,
            user_repo,
            credential_repo,
            PBKDF2PasswordHasher(iterations=1_000),
            HMACTokenService(secret="test-secret"),
        )

    def test_register_user_stores_hashed_credentials(
        self, use_cases, credential_repo
    ):
        user = use_cases.register_user(
            CreateUserDTO(
                username="john_doe",
                email="john@example.com",
                password="password123",
            )
        )

        credential = credential_repo.get_by_user_id(user.id)
        assert credential is not None
        assert credential.username == "john_doe"
        assert credential.password_hash != "password123"

    def test_login_returns_bearer_token(self, use_cases):
        user = use_cases.register_user(
            CreateUserDTO(
                username="john_doe",
                email="john@example.com",
                password="password123",
            )
        )

        token = use_cases.login(
            LoginDTO(username="john_doe", password="password123")
        )

        assert token.token_type == "bearer"
        assert token.user_id == user.id
        assert use_cases.authenticate_token(token.access_token) == user.id

    def test_login_rejects_invalid_password(self, use_cases):
        use_cases.register_user(
            CreateUserDTO(
                username="john_doe",
                email="john@example.com",
                password="password123",
            )
        )

        with pytest.raises(AuthenticationFailedException):
            use_cases.login(
                LoginDTO(username="john_doe", password="wrong-password")
            )

    def test_authenticate_token_rejects_invalid_token(self, use_cases):
        with pytest.raises(AuthenticationFailedException):
            use_cases.authenticate_token("not-a-token")
