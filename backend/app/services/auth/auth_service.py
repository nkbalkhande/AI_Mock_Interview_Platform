"""Authentication service — login logic.

Owns the credential-verification workflow: look up the user, verify the
password, reject inactive accounts, stamp ``last_login_at``, and issue tokens.
It commits its own unit of work for the request since login is a self-contained
transaction (login timestamp + refresh token row).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, AuthenticationError
from app.domain.enums import RoleName
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_role import UserRole
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.auth.password_service import PasswordService
from app.services.auth.token_service import IssuedTokens, TokenService


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    tokens: IssuedTokens


@dataclass(frozen=True)
class ResumeFileRef:
    """Storage metadata for an already-persisted resume file.

    The router saves the upload via the storage service and passes this in, so
    the service layer never touches the filesystem or the web framework.
    """

    file_name: str
    file_path: str
    file_type: str
    file_size_bytes: int


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        password_service: PasswordService | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.passwords = password_service or PasswordService()
        self.tokens = token_service or TokenService(session)

    async def register(
        self,
        full_name: str,
        email: str,
        password: str,
        *,
        current_organization: str,
        current_designation: str,
        years_of_experience: Decimal,
        resume: ResumeFileRef,
        phone_number: str | None = None,
        profile_photo_path: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthenticatedUser:
        """Create a candidate account (identity + profile + resume) and log in.

        Writes across ``users``, ``user_profiles``, ``resumes`` and
        ``resume_versions`` in a single transaction, grants the default
        CANDIDATE role, and issues tokens so signup logs the user straight in.

        Raises ``AlreadyExistsError`` if the email is already taken (matched
        case-insensitively against the ``lower(email)`` unique index).
        """
        full_name = full_name.strip()
        email = email.strip()

        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise AlreadyExistsError("An account with this email already exists.")

        role = await self.roles.get_by_name(RoleName.CANDIDATE)
        if role is None:  # pragma: no cover - indicates missing role seed
            raise RuntimeError(
                "Default role 'CANDIDATE' is not seeded; cannot register users."
            )

        user = User(
            full_name=full_name,
            email=email,
            password_hash=self.passwords.hash(password),
        )
        # Attaching the Role object lets the response read `ur.role.name`
        # without an extra query, and cascade inserts the association row.
        user.user_roles.append(UserRole(role=role))

        # 1:1 extended profile.
        user.profile = UserProfile(
            current_organization=current_organization.strip(),
            current_designation=current_designation.strip(),
            years_of_experience=years_of_experience,
            phone_number=(phone_number.strip() if phone_number else None),
            profile_photo_path=profile_photo_path,
        )

        # Resume as version 1 (marked current). Text extraction is deferred to a
        # background task, so ``extracted_text`` starts null.
        user.resume = Resume(
            current_version_number=1,
            versions=[
                ResumeVersion(
                    version_number=1,
                    file_name=resume.file_name,
                    file_path=resume.file_path,
                    file_type=resume.file_type,
                    file_size_bytes=resume.file_size_bytes,
                    is_current=True,
                )
            ],
        )

        self.session.add(user)
        await self.session.flush()

        issued = await self.tokens.issue_for_user(
            user.id, user_agent=user_agent, ip_address=ip_address
        )

        await self.session.commit()
        return AuthenticatedUser(user=user, tokens=issued)

    async def login(
        self,
        email: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthenticatedUser:
        """Authenticate credentials and issue tokens.

        Raises ``AuthenticationError`` for unknown email, wrong password, or a
        deactivated account. The error message is intentionally generic to avoid
        leaking which accounts exist.
        """
        invalid = AuthenticationError("Invalid email or password.")

        user = await self.users.get_by_email(email)
        if user is None:
            # Verify against a dummy hash to keep timing roughly constant and
            # avoid revealing whether the email exists.
            self.passwords.verify(password, _DUMMY_HASH)
            raise invalid

        if not self.passwords.verify(password, user.password_hash):
            raise invalid

        if not user.is_active:
            raise AuthenticationError("This account is disabled.")

        user.last_login_at = datetime.now(timezone.utc)

        issued = await self.tokens.issue_for_user(
            user.id, user_agent=user_agent, ip_address=ip_address
        )

        await self.session.commit()
        return AuthenticatedUser(user=user, tokens=issued)


# Pre-computed valid bcrypt hash, used only to equalize timing on the
# "user not found" path (the plaintext behind it is irrelevant/unusable).
_DUMMY_HASH = "$2b$12$ZalhNgMT7j12kkMr3kFkru6yuTcBtiiljj/KezU2NsiOLmA5MNU2."
