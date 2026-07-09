"""Authentication use cases."""

from datetime import datetime

from app.application.dto.auth_dto import AuthTokenDTO, LoginDTO
from app.application.dto.user_dto import CreateUserDTO, UserResponseDTO
from app.application.security import PasswordHasher, TokenService
from app.application.use_cases.user_use_cases import UserUseCases
from app.domain.entities.auth import UserCredential
from app.domain.exceptions import AuthenticationFailedException
from app.domain.repositories.credential_repository import CredentialRepository
from app.domain.repositories.user_repository import UserRepository


class AuthenticationUseCases:
    """Orchestrates registration, login, and token verification."""

    def __init__(
        self,
        user_use_cases: UserUseCases,
        user_repository: UserRepository,
        credential_repository: CredentialRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.user_use_cases = user_use_cases
        self.user_repository = user_repository
        self.credential_repository = credential_repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def register_user(self, dto: CreateUserDTO) -> UserResponseDTO:
        """Create a user profile and its login credentials."""
        user = self.user_use_cases.create_user(dto)
        credential = UserCredential(
            user_id=user.id,
            username=user.username,
            password_hash=self.password_hasher.hash_password(dto.password),
            created_at=datetime.utcnow(),
        )
        self.credential_repository.save(credential)
        return user

    def login(self, dto: LoginDTO) -> AuthTokenDTO:
        """Authenticate username/password and issue an access token."""
        credential = self.credential_repository.get_by_username(dto.username)
        if not credential:
            raise AuthenticationFailedException()

        if not self.password_hasher.verify_password(
            dto.password, credential.password_hash
        ):
            raise AuthenticationFailedException()

        user = self.user_repository.get_by_id(credential.user_id)
        if not user:
            raise AuthenticationFailedException()

        return AuthTokenDTO(
            access_token=self.token_service.issue_token(user.id),
            token_type="bearer",
            user_id=user.id,
            username=user.username,
        )

    def authenticate_token(self, token: str) -> str:
        """Return the authenticated user ID for a bearer token."""
        user_id = self.token_service.verify_token(token)
        if not user_id or not self.user_repository.get_by_id(user_id):
            raise AuthenticationFailedException("Invalid or expired token")
        return user_id
