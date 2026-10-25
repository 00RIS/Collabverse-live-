
from authlib.integrations.starlette_client import OAuth

from app.core.config import settings


oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    # Keep discovery metadata local so the initial login redirect does not
    # depend on an extra Google metadata request from the API process.
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    issuer="https://accounts.google.com",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    id_token_signing_alg_values_supported=["RS256"],
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",
    },
)
