
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.uploads import cloud_storage_enabled, get_cloud_blob

from app.modules.ai_mentor.routes import (
    router as ai_mentor_router,
)
from app.modules.profiles.routes import (
    router as profiles_router,
)
from app.modules.posts.routes import (
    router as posts_router,
)
from app.modules.notifications.routes import (
    router as notifications_router,
)
from app.modules.mentorship.routes import (
    router as mentorship_router,
)
from app.modules.professionals.routes import (
    router as professionals_router,
)
from app.modules.preferences.routes import (
    router as preferences_router,
)
from app.modules.daily_assessment.routes import (
    router as daily_assessment_router,
)
from app.modules.news.routes import router as news_router
from app.modules.recommendations.routes import (
    router as recommendations_router,
)
from app.modules.home.routes import (
    router as home_router,
)
from app.modules.hackathons.routes import (
    router as hackathons_router,
)

# Messaging
from app.modules.messaging.routes import (
    router as messaging_router,
)
from app.modules.messaging.websocket import (
    router as messaging_websocket_router,
)


app = FastAPI(
    title="Academia Industry Collaboration API",
    version="1.0.0",
)

if cloud_storage_enabled():
    @app.get("/uploads/{object_name:path}", include_in_schema=False)
    def get_upload(object_name: str):
        if object_name.startswith("/") or ".." in Path(object_name).parts:
            raise HTTPException(status_code=404, detail="Upload not found")
        try:
            blob = get_cloud_blob(object_name)
            if blob is None:
                raise HTTPException(status_code=404, detail="Upload not found")

            def content_stream():
                with blob.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        yield chunk

            headers = {"Cache-Control": "public, max-age=3600"}
            if blob.size is not None:
                headers["Content-Length"] = str(blob.size)
            return StreamingResponse(
                content_stream(),
                media_type=blob.content_type or "application/octet-stream",
                headers=headers,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Could not retrieve the upload from cloud storage") from exc
else:
    app.mount(
        "/uploads",
        StaticFiles(directory=Path(__file__).resolve().parent.parent / "uploads"),
        name="uploads",
    )


# ============================================================
# GOOGLE OAUTH SESSION MIDDLEWARE
# ============================================================

# Authlib stores temporary OAuth state in a signed session
# cookie so it can validate Google's callback.
#
# Use a strong SECRET_KEY from backend/.env.
# Never store Google client credentials in the frontend.

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="collabverse_oauth_session",
    max_age=600,
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CORE API ROUTER
# ============================================================

app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX,
)


# ============================================================
# MODULE ROUTERS
# ============================================================

app.include_router(
    ai_mentor_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    profiles_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    posts_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    notifications_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    mentorship_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    professionals_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    preferences_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    daily_assessment_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    news_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    recommendations_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    home_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    hackathons_router,
    prefix=settings.API_V1_PREFIX,
)


# ============================================================
# MESSAGING
# ============================================================

app.include_router(
    messaging_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    messaging_websocket_router,
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": (
            "Academia Industry Collaboration API is running"
        )
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
