"""Upload storage with a local development mode and private Google Cloud Storage."""

import json
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


UPLOAD_ROOT = (
    Path(settings.UPLOADS_DIR).resolve()
    if settings.UPLOADS_DIR.strip()
    else Path(__file__).resolve().parents[2] / "uploads"
)


def cloud_storage_enabled() -> bool:
    return bool(settings.GCS_BUCKET_NAME.strip())


def cloudinary_storage_enabled() -> bool:
    return all(
        value.strip()
        for value in (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    )


@lru_cache(maxsize=1)
def _storage_client():
    from google.cloud import storage

    if settings.GCS_SERVICE_ACCOUNT_JSON.strip():
        from google.oauth2 import service_account

        service_account_info = json.loads(settings.GCS_SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        return storage.Client(
            project=service_account_info.get("project_id"),
            credentials=credentials,
        )

    return storage.Client()


@lru_cache(maxsize=1)
def _configure_cloudinary():
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    return cloudinary


if not cloud_storage_enabled() and not cloudinary_storage_enabled():
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def save_upload(file_obj: BinaryIO, object_name: str, content_type: str) -> str | None:
    """Persist an upload in Cloudinary, GCS, or local development storage.

    Returns a hosted URL for Cloudinary uploads; local and GCS uploads keep
    using the existing backend /uploads URL convention.
    """
    file_obj.seek(0)
    cloudinary_requested = any(
        value.strip()
        for value in (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    )
    if cloudinary_requested and not cloudinary_storage_enabled():
        raise RuntimeError("Set all three Cloudinary credentials to enable Cloudinary uploads")

    if cloudinary_storage_enabled():
        cloudinary = _configure_cloudinary()
        extensionless_name = str(Path(object_name).with_suffix(""))
        resource_type = "video" if content_type.startswith("video/") else "image"
        result = cloudinary.uploader.upload(
            file_obj,
            public_id=f"collabverse/{extensionless_name}",
            resource_type=resource_type,
            overwrite=False,
            unique_filename=False,
            use_filename=False,
            timeout=180,
        )
        secure_url = result.get("secure_url")
        if not secure_url:
            raise RuntimeError("Cloudinary did not return a secure media URL")
        return secure_url

    if cloud_storage_enabled():
        blob = _storage_client().bucket(settings.GCS_BUCKET_NAME).blob(object_name)
        blob.upload_from_file(
            file_obj,
            rewind=True,
            content_type=content_type,
            timeout=180,
        )
        return None

    destination = (UPLOAD_ROOT / object_name).resolve()
    if destination != UPLOAD_ROOT.resolve() and UPLOAD_ROOT.resolve() not in destination.parents:
        raise ValueError("Invalid upload path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := file_obj.read(1024 * 1024):
            output.write(chunk)
    return None


def get_cloud_blob(object_name: str):
    """Return a GCS blob after checking it exists; caller streams its contents."""
    if not cloud_storage_enabled():
        raise RuntimeError("Google Cloud Storage is not configured")

    blob = _storage_client().bucket(settings.GCS_BUCKET_NAME).blob(object_name)
    if not blob.exists():
        return None
    blob.reload()
    return blob
