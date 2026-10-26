import uuid
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.uploads import UPLOAD_ROOT, save_upload
from app.db.session import get_db
from app.models.user import User, UserRole

from .schemas import (
    AcademicianProfileResponse,
    AcademicianProfileUpdate,
    InstitutionProfileResponse,
    InstitutionProfileUpdate,
    ProfessionalProfileResponse,
    ProfessionalProfileUpdate,
    RecruiterProfileResponse,
    RecruiterProfileUpdate,
    StudentProfileResponse,
    StudentProfileUpdate,
)

from .service import profile_service


router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"],
)

AVATAR_DIR = UPLOAD_ROOT / "avatars"
MAX_AVATAR_BYTES = 5 * 1024 * 1024
AVATAR_TYPES = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".webp": ("image/webp", b"RIFF"),
}


def serialize_profile(
    user: User,
    profile,
):
    if user.role == UserRole.STUDENT:
        return StudentProfileResponse.model_validate(
            profile
        ).model_dump()

    if user.role == UserRole.RECRUITER:
        return RecruiterProfileResponse.model_validate(
            profile
        ).model_dump()

    if user.role == UserRole.ACADEMICIAN:
        return AcademicianProfileResponse.model_validate(
            profile
        ).model_dump()

    if user.role == UserRole.PROFESSIONAL:
        return ProfessionalProfileResponse.model_validate(
            profile
        ).model_dump()

    if user.role == UserRole.INSTITUTION_ADMIN:
        return InstitutionProfileResponse.model_validate(
            profile
        ).model_dump()

    raise HTTPException(
        status_code=400,
        detail="Unsupported user role",
    )


@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = profile_service.get_profile(
        db=db,
        user=current_user,
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "avatar_url": current_user.avatar_url,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }


@router.post("/me/avatar")
def upload_profile_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix.lower()
    config = AVATAR_TYPES.get(suffix)
    if config is None or file.content_type != config[0]:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WebP image.")

    stored_name = f"{current_user.id}-{uuid.uuid4().hex}{suffix}"
    total = 0
    first_chunk = True
    try:
        with SpooledTemporaryFile(max_size=5 * 1024 * 1024, mode="w+b") as output:
            while chunk := file.file.read(1024 * 1024):
                if first_chunk:
                    signature = config[1]
                    valid = chunk.startswith(signature)
                    if suffix == ".webp":
                        valid = chunk.startswith(b"RIFF") and chunk[8:12] == b"WEBP"
                    if not valid:
                        raise HTTPException(status_code=415, detail="The file contents do not match the selected image type.")
                    first_chunk = False
                total += len(chunk)
                if total > MAX_AVATAR_BYTES:
                    raise HTTPException(status_code=413, detail="Profile photos must be 5 MB or smaller.")
                output.write(chunk)
            if total == 0:
                raise HTTPException(status_code=400, detail="The selected file is empty.")
            hosted_url = save_upload(output, f"avatars/{stored_name}", config[0])
        old_url = current_user.avatar_url
        current_user.avatar_url = hosted_url or f"{str(request.base_url).rstrip('/')}/uploads/avatars/{stored_name}"
        db.commit()
        db.refresh(current_user)
        if old_url and "/uploads/avatars/" in old_url and not settings.GCS_BUCKET_NAME:
            old_path = (AVATAR_DIR / old_url.rsplit("/", 1)[-1]).resolve()
            if old_path.parent == AVATAR_DIR.resolve():
                old_path.unlink(missing_ok=True)
        return {"avatar_url": current_user.avatar_url}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not store the profile photo. Check the configured upload storage and try again.") from exc
    finally:
        file.file.close()


@router.patch("/me/student")
def update_student_profile(
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for student profiles",
        )

    profile = profile_service.update_profile(
        db=db,
        user=current_user,
        update_data=payload.model_dump(
            exclude_unset=True
        ),
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }


@router.patch("/me/recruiter")
def update_recruiter_profile(
    payload: RecruiterProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for recruiter profiles",
        )

    profile = profile_service.update_profile(
        db=db,
        user=current_user,
        update_data=payload.model_dump(
            exclude_unset=True
        ),
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }


@router.patch("/me/academician")
def update_academician_profile(
    payload: AcademicianProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ACADEMICIAN:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for academician profiles",
        )

    profile = profile_service.update_profile(
        db=db,
        user=current_user,
        update_data=payload.model_dump(
            exclude_unset=True
        ),
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }


@router.patch("/me/professional")
def update_professional_profile(
    payload: ProfessionalProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PROFESSIONAL:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for professional profiles",
        )

    profile = profile_service.update_profile(
        db=db,
        user=current_user,
        update_data=payload.model_dump(
            exclude_unset=True
        ),
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }


@router.patch("/me/institution")
def update_institution_profile(
    payload: InstitutionProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.INSTITUTION_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only for institution admin profiles",
        )

    profile = profile_service.update_profile(
        db=db,
        user=current_user,
        update_data=payload.model_dump(
            exclude_unset=True
        ),
    )

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "profile": serialize_profile(
            current_user,
            profile,
        ),
    }
