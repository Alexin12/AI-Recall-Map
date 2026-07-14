"""Authentication: verify a Supabase (GoTrue) JWT and expose the user id.

Supabase Auth signs access tokens with an asymmetric key (ES256) and publishes
the public keys at a JWKS endpoint, so we verify signatures against that.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import SUPABASE_URL

_bearer = HTTPBearer() #grab jwt token 
_jwks = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")# the address to get public key


def current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Return the authenticated user's id (the JWT ``sub`` claim).

    Verifies the ES256 signature against Supabase's JWKS and the
    ``authenticated`` audience that Supabase Auth stamps on access tokens.
    """
    token = credentials.credentials
    try:
        signing_key = _jwks.get_signing_key_from_jwt(token)#Get correct public key for the token , to decode
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):# Signiture can be changed, 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return payload["sub"]
