"""Upload storage with a local development mode and private Google Cloud Storage."""

from pathlib import Path
from functools import lru_cache
from typing import BinaryIO

from app.core.config import settings


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"


def cloud_storage_enabled() -> bool:
    return bool(settings.GCS_BUCKET_NAME.strip())


@lru_cache(maxsize=1)
def _storage_client():
    from google.cloud import storage

    return storage.Client()


def save_upload(file_obj: BinaryIO, object_name: str, content_type: str) -> None:
    """Persist an already-validated upload, using ADC when GCS is configured."""
    file_obj.seek(0)
    if cloud_storage_enabled():
        blob = _storage_client().bucket(settings.GCS_BUCKET_NAME).blob(object_name)
        blob.upload_from_file(
            file_obj,
            rewind=True,
            content_type=content_type,
            timeout=180,
        )
        return

    destination = (UPLOAD_ROOT / object_name).resolve()
    if destination != UPLOAD_ROOT.resolve() and UPLOAD_ROOT.resolve() not in destination.parents:
        raise ValueError("Invalid upload path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while chunk := file_obj.read(1024 * 1024):
            output.write(chunk)


def get_cloud_blob(object_name: str):
    """Return a GCS blob after checking it exists; caller streams its contents."""
    if not cloud_storage_enabled():
        raise RuntimeError("Google Cloud Storage is not configured")

    blob = _storage_client().bucket(settings.GCS_BUCKET_NAME).blob(object_name)
    if not blob.exists():
        return None
    blob.reload()
    return blob
