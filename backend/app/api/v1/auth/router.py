"""Auth API routes.

Currently exposes login. Tokens are set as httpOnly cookies so the browser
never handles them in JS: ``session`` carries the access JWT (the name the
Next.js middleware checks) and ``refresh_token`` carries the opaque refresh
token.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.dependencies.storage import get_storage_service
from app.api.v1.auth.schemas import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from app.models.user import User
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.services.auth.auth_service import (
    AuthenticatedUser,
    AuthService,
    ResumeFileRef,
)
from app.services.resumes.resume_ingestion_service import ingest_resume_version
from app.services.storage.file_storage import FileStorageService, StoredFile

router = APIRouter()

ACCESS_COOKIE_NAME = "session"  # noqa: S105 - cookie name, not a secret
REFRESH_COOKIE_NAME = "refresh_token"  # noqa: S105 - cookie name, not a secret

# Accepted upload content types.
_RESUME_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
)
_PHOTO_CONTENT_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/jpg", "image/webp"}
)


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


def _set_auth_cookies(response: Response, result: AuthenticatedUser) -> None:
    common = {
        "httponly": True,
        "secure": settings.is_production,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        result.tokens.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        result.tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **common,
    )


def _build_auth_response(result: AuthenticatedUser) -> LoginResponse:
    roles = [ur.role.name for ur in result.user.user_roles if ur.role is not None]
    profile = getattr(result.user, "profile", None)
    return LoginResponse(
        user=AuthUser(
            id=result.user.id,
            full_name=result.user.full_name,
            email=result.user.email,
            roles=roles,
            profile_photo_path=profile.profile_photo_path if profile else None,
        )
    )


@router.get("/me", response_model=AuthUser)
async def me(current_user: User = Depends(get_current_user)) -> AuthUser:
    """Return the currently authenticated user's identity.

    Used by the frontend on app boot / page refresh to rehydrate its client
    auth store from the httpOnly ``session`` cookie (JS can't read the cookie
    itself). Returns 401 through the auth dependency when no valid session
    is present.
    """
    roles = [ur.role.name for ur in current_user.user_roles if ur.role is not None]
    profile = getattr(current_user, "profile", None)
    return AuthUser(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        roles=roles,
        profile_photo_path=profile.profile_photo_path if profile else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    """Clear the auth cookies. Idempotent; no session lookup required.

    Deleting the cookies is enough for the browser to lose access; the
    matching refresh-token row can be revoked separately later — this is
    the pragmatic MVP behavior and matches how the login flow only sets
    cookies (no server-side session state to invalidate).
    """
    common = {"path": "/", "httponly": True, "samesite": "lax"}
    response.delete_cookie(ACCESS_COOKIE_NAME, **common)
    response.delete_cookie(REFRESH_COOKIE_NAME, **common)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    result = await service.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    _set_auth_cookies(response, result)
    return _build_auth_response(result)


def _schedule_resume_ingestion(
    background_tasks: BackgroundTasks, result: AuthenticatedUser
) -> None:
    """Kick off parse -> chunk -> embed -> Qdrant upsert after the response.

    Runs via ``BackgroundTasks`` (not Celery) for MVP scope: it's fire-and-forget,
    doesn't block the signup response, and needs no extra infra. The resume
    row/version is already committed, so a failure here never affects signup.
    """
    resume = getattr(result.user, "resume", None)
    if resume is None or not resume.versions:
        return
    current_version = next((v for v in resume.versions if v.is_current), resume.versions[0])
    background_tasks.add_task(
        ingest_resume_version,
        resume_version_id=current_version.id,
        user_id=result.user.id,
    )


async def _read_validated_upload(
    upload: UploadFile,
    *,
    allowed_types: frozenset[str],
    field: str,
) -> bytes:
    """Read an upload into memory, enforcing size + content-type limits."""
    data = await upload.read()
    if not data:
        raise ValidationError(f"The {field} file is empty.")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise ValidationError(
            f"The {field} file exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )

    content_type = (upload.content_type or "").lower()
    if content_type not in allowed_types:
        raise ValidationError(
            f"Unsupported {field} file type: {content_type or 'unknown'}."
        )
    return data


async def _optional_upload(request: Request, field: str) -> UploadFile | None:
    """Pull an optional file from the parsed multipart form.

    We read it from the (cached) form rather than declaring it as a typed
    ``UploadFile | None`` parameter, which can raise a request-validation error
    at parse time on some FastAPI/Pydantic combinations when a file is attached.
    """
    form = await request.form()
    value = form.get(field)
    if isinstance(value, StarletteUploadFile) and value.filename:
        return value
    return None


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    current_organization: str = Form(...),
    current_designation: str = Form(...),
    years_of_experience: Decimal = Form(...),
    phone_number: str | None = Form(None),
    resume: UploadFile = File(...),
    service: AuthService = Depends(get_auth_service),
    storage: FileStorageService = Depends(get_storage_service),
) -> LoginResponse:
    """Create a candidate account (with resume) and sign them in via cookies.

    Accepts ``multipart/form-data`` because the resume (and optional photo) are
    file uploads. Text fields are validated through ``RegisterRequest``; files
    are validated and persisted before the DB transaction, and rolled back from
    storage if that transaction fails.
    """
    # Validate the text fields with the same rules as the JSON schema, mapping
    # pydantic errors onto our consistent {error:{...}} envelope.
    try:
        payload = RegisterRequest(
            full_name=full_name,
            email=email,
            password=password,
            current_organization=current_organization,
            current_designation=current_designation,
            years_of_experience=years_of_experience,
            phone_number=phone_number,
        )
    except PydanticValidationError as exc:
        raise ValidationError(
            "Invalid registration details.", details=exc.errors()
        ) from exc

    resume_bytes = await _read_validated_upload(
        resume, allowed_types=_RESUME_CONTENT_TYPES, field="resume"
    )
    stored_resume = storage.save(
        category="resumes",
        original_name=resume.filename or "resume",
        data=resume_bytes,
        content_type=(resume.content_type or "application/octet-stream"),
    )

    stored_photo: StoredFile | None = None
    profile_photo = await _optional_upload(request, "profile_photo")
    if profile_photo is not None:
        photo_bytes = await _read_validated_upload(
            profile_photo, allowed_types=_PHOTO_CONTENT_TYPES, field="profile photo"
        )
        stored_photo = storage.save(
            category="photos",
            original_name=profile_photo.filename,
            data=photo_bytes,
            content_type=(profile_photo.content_type or "application/octet-stream"),
        )

    try:
        result = await service.register(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            current_organization=payload.current_organization,
            current_designation=payload.current_designation,
            years_of_experience=payload.years_of_experience,
            phone_number=payload.phone_number,
            resume=ResumeFileRef(
                file_name=stored_resume.file_name,
                file_path=stored_resume.file_path,
                file_type=stored_resume.content_type,
                file_size_bytes=stored_resume.size_bytes,
            ),
            profile_photo_path=stored_photo.file_path if stored_photo else None,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except Exception:
        # Roll back files we just wrote so a failed signup leaves no orphans.
        storage.delete(stored_resume.file_path)
        if stored_photo is not None:
            storage.delete(stored_photo.file_path)
        raise

    _schedule_resume_ingestion(background_tasks, result)
    _set_auth_cookies(response, result)
    return _build_auth_response(result)
