from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, cast

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.config import get_settings


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token",
    auto_error=False,
)


@dataclass(frozen=True)
class CurrentUser:
    subject: str
    roles: set[str]

def create_access_token(
    subject: str,
    roles: list[str],
    expires_delta: timedelta | None = None,
    ) -> str:
    settings = get_settings()

    now = datetime.now(timezone.utc)
    expires_at = now + (expires_delta or timedelta(minutes=60))

    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return cast(str, token)



def _unauthorized_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> CurrentUser:
    if token is None:
        raise _unauthorized_exception()

    settings = get_settings()

    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            ),
        )
    except InvalidTokenError as error:
        raise _unauthorized_exception() from error

    subject = payload.get("sub")
    roles_claim = payload.get("roles", [])

    if not isinstance(subject, str) or not subject:
        raise _unauthorized_exception()

    if not isinstance(roles_claim, list) or not all(
        isinstance(role, str) for role in roles_claim
    ):
        raise _unauthorized_exception()

    return CurrentUser(
        subject=subject,
        roles=set(roles_claim),
    )


def require_role(required_role: str) -> Callable[[CurrentUser], CurrentUser]:
    def role_checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {required_role}",
            )

        return current_user

    return role_checker