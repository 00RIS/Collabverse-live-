
"""
CollabVerse authentication endpoints.

Verified Google account creation and sign-in:
- GET  /auth/google/login
- GET  /auth/google/callback
- POST /auth/google/exchange
- POST /auth/google/signup

Email/password registration is disabled. A password may be set during the
Google-verified signup and used for later sign-in; password login is only
allowed for accounts linked to a verified Google identity.

"""

import hashlib
import logging
import secrets
import uuid

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from authlib.integrations.base_client import OAuthError
from httpx import HTTPError as HTTPXError

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import RedirectResponse

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.oauth import oauth
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

from app.db.session import get_db

from app.models.oauth_account import OAuthAccount
from app.models.pending_oauth import PendingOAuth

from app.models.profile import (
    AcademicianProfile,
    InstitutionProfile,
    RecruiterProfile,
    StudentProfile,
)
from app.models.user import User, UserRole
from app.modules.professionals.models import ProfessionalProfile

from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserOut


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

OAUTH_CODE_LIFETIME = timedelta(minutes=5)
TERMS_VERSION = "2026-10-24"


# ============================================================
# GOOGLE REQUEST SCHEMAS
# ============================================================

class GoogleExchangeRequest(BaseModel):
    code: str = Field(min_length=20, max_length=256)


class GoogleSignupRequest(BaseModel):
    code: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    full_name: str = Field(min_length=1, max_length=255)
    company_name: str | None = None
    institution_name: str | None = None
    accepted_terms: bool = False
    website: str = ""


# ============================================================
# SHARED HELPERS
# ============================================================

def issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


def hash_exchange_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def consume_pending_code(
    db: Session,
    code: str,
) -> PendingOAuth:
    """
    Atomically delete and return a pending OAuth record.

    PostgreSQL DELETE ... RETURNING ensures concurrent
    requests cannot successfully consume the same code.
    """
    record = db.scalar(
        delete(PendingOAuth)
        .where(
            PendingOAuth.code_hash == hash_exchange_code(code)
        )
        .returning(PendingOAuth)
    )

    if record is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or already-used Google login code",
        )

    if record.expires_at <= datetime.now(timezone.utc):
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Google login code has expired",
        )

    return record


def build_profile(
    user_id,
    role,
    full_name,
    company_name=None,
    institution_name=None,
):
    full_name = full_name.strip()
    company_name = (
        company_name.strip() if company_name else None
    )
    institution_name = (
        institution_name.strip() if institution_name else None
    )

    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="full_name is required",
        )

    if role == UserRole.STUDENT:
        return StudentProfile(
            user_id=user_id,
            full_name=full_name,
        )

    if role == UserRole.RECRUITER:
        if not company_name:
            raise HTTPException(
                status_code=400,
                detail="company_name is required for recruiters",
            )

        return RecruiterProfile(
            user_id=user_id,
            full_name=full_name,
            company_name=company_name,
        )

    if role == UserRole.ACADEMICIAN:
        if not institution_name:
            raise HTTPException(
                status_code=400,
                detail="institution_name is required for academicians",
            )

        return AcademicianProfile(
            user_id=user_id,
            full_name=full_name,
            institution_name=institution_name,
        )

    if role == UserRole.PROFESSIONAL:
        return ProfessionalProfile(
            user_id=user_id,
            full_name=full_name,
            company_name=company_name,
        )

    if role == UserRole.INSTITUTION_ADMIN:
        if not institution_name:
            raise HTTPException(
                status_code=400,
                detail="institution_name is required for institution admins",
            )

        return InstitutionProfile(
            user_id=user_id,
            admin_name=full_name,
            institution_name=institution_name,
        )

    raise HTTPException(
        status_code=400,
        detail="Unsupported user role",
    )


# ============================================================
# EXISTING EMAIL / PASSWORD REGISTRATION
# ============================================================

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Create your account with a verified Google account.",
    )


# ============================================================
# EXISTING EMAIL / PASSWORD LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not user.is_email_verified
        or not user.hashed_password
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    linked_google_account = db.scalar(
        select(OAuthAccount.id).where(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == "google",
        )
    )
    if linked_google_account is None:
        raise HTTPException(
            status_code=403,
            detail="This account must be created and verified with Google before password sign-in is enabled.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return issue_tokens(user)


# ============================================================
# EXISTING REFRESH TOKEN
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    token_payload = decode_token(payload.refresh_token)

    if (
        token_payload is None
        or token_payload.get("type") != "refresh"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    try:
        user_uuid = uuid.UUID(token_payload.get("sub"))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    user = db.get(User, user_uuid)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    linked_google_account = db.scalar(
        select(OAuthAccount.id).where(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == "google",
        )
    )
    if linked_google_account is None or not user.is_email_verified:
        raise HTTPException(
            status_code=401,
            detail="A verified Google account is required",
        )

    return issue_tokens(user)


# ============================================================
# GOOGLE OAUTH — START
# ============================================================

@router.get("/google/login")
async def google_login(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server")
    try:
        return await oauth.google.authorize_redirect(
            request,
            settings.GOOGLE_REDIRECT_URI,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not start Google OAuth authorization")
        raise HTTPException(
            status_code=502,
            detail=f"Google sign-in could not start ({type(exc).__name__}). Check the backend log and retry.",
        ) from exc


# ============================================================
# GOOGLE OAUTH — CALLBACK
# ============================================================

@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):

    try:
        token = await oauth.google.authorize_access_token(
            request
        )
    except OAuthError:
        raise HTTPException(
            status_code=401,
            detail="Google authentication failed",
        )
    except HTTPXError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Google to complete sign-in. Check the backend internet connection and try again.",
        )

    # Authlib verifies the OIDC ID token and nonce.
    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(
            status_code=401,
            detail="Google identity information missing",
        )

    google_sub = userinfo.get("sub")
    email = userinfo.get("email")

    if (
        not google_sub
        or not email
        or userinfo.get("email_verified") is not True
    ):
        raise HTTPException(
            status_code=401,
            detail="Google identity is not verified",
        )

    linked_account = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == google_sub,
        )
    )

    linked_user = None

    if linked_account is not None:
        linked_user = db.get(
            User,
            linked_account.user_id,
        )

        if linked_user is None or not linked_user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account unavailable",
            )

        flow = "login"

    else:
        # Never automatically link an existing account
        # based only on a matching email.
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user is not None:
            return RedirectResponse(
                url=(
                    settings.FRONTEND_URL.rstrip("/")
                    + "/login?google=account_exists"
                ),
                status_code=303,
            )

        flow = "signup"

    # Generate a high-entropy, one-time exchange code.
    raw_code = secrets.token_urlsafe(32)

    pending = PendingOAuth(
        code_hash=hash_exchange_code(raw_code),
        provider="google",
        provider_user_id=google_sub,
        provider_email=email,
        display_name=userinfo.get("name"),
        user_id=linked_user.id if linked_user else None,
        expires_at=(
            datetime.now(timezone.utc)
            + OAUTH_CODE_LIFETIME
        ),
    )

    db.add(pending)
    db.commit()

    # Remove any old temporary session identity.
    request.session.pop(
        "oauth_authenticated_user_id",
        None,
    )
    request.session.pop(
        "google_pending_signup",
        None,
    )

    destination = (
        "/login" if flow == "login" else "/register"
    )

    query = urlencode({
        "google": flow,
        "code": raw_code,
    })

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL.rstrip('/')}{destination}?{query}",
        status_code=303,
    )


# ============================================================
# GOOGLE OAUTH — EXISTING ACCOUNT EXCHANGE
# ============================================================

@router.post(
    "/google/exchange",
    response_model=TokenResponse,
)
def google_exchange(
    payload: GoogleExchangeRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    try:
        pending = consume_pending_code(
            db,
            payload.code,
        )

        if (
            pending.provider != "google"
            or pending.user_id is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Code is not valid for Google login",
            )

        user = db.get(User, pending.user_id)

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account unavailable",
            )

        # Confirm the provider identity is still linked.
        linked = db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user.id,
                OAuthAccount.provider == "google",
                OAuthAccount.provider_user_id
                == pending.provider_user_id,
            )
        )

        if linked is None:
            raise HTTPException(
                status_code=401,
                detail="Google account is not linked",
            )

        user.last_login_at = datetime.now(timezone.utc)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return issue_tokens(user)


# ============================================================
# GOOGLE OAUTH — FIRST-TIME SIGNUP
# ============================================================

@router.post(
    "/google/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def google_signup(
    payload: GoogleSignupRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    if payload.website.strip():
        raise HTTPException(status_code=400, detail="Unable to create account")
    if not payload.accepted_terms:
        raise HTTPException(status_code=400, detail="You must accept the Terms of Service to create an account")

    # Validate profile fields before consuming the code.
    # This allows users to correct incomplete forms.
    build_profile(
        user_id=uuid.uuid4(),
        role=payload.role,
        full_name=payload.full_name,
        company_name=payload.company_name,
        institution_name=payload.institution_name,
    )

    try:
        pending = consume_pending_code(
            db,
            payload.code,
        )

        if (
            pending.provider != "google"
            or pending.user_id is not None
        ):
            raise HTTPException(
                status_code=400,
                detail="Code is not valid for Google signup",
            )

        existing_user = db.scalar(
            select(User).where(
                User.email == pending.provider_email
            )
        )

        existing_identity = db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.provider == "google",
                OAuthAccount.provider_user_id
                == pending.provider_user_id,
            )
        )

        if existing_user or existing_identity:
            raise HTTPException(
                status_code=409,
                detail="Account already exists",
            )

        user = User(
            email=pending.provider_email,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            is_email_verified=True,
            terms_accepted_at=datetime.now(timezone.utc),
            terms_version=TERMS_VERSION,
        )

        db.add(user)
        db.flush()

        profile = build_profile(
            user_id=user.id,
            role=payload.role,
            full_name=payload.full_name,
            company_name=payload.company_name,
            institution_name=payload.institution_name,
        )

        oauth_identity = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=pending.provider_user_id,
            provider_email=pending.provider_email,
        )

        db.add(profile)
        db.add(oauth_identity)

        user.last_login_at = datetime.now(timezone.utc)

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Account already exists",
        )

    except Exception:
        db.rollback()
        raise

    return issue_tokens(user)
