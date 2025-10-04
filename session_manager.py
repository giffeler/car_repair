"""
session_manager.py

Provides JWT-based authentication for FastAPI dependencies.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY") or ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token with expiration.

    Parameters
    ----------
    data : Dict[str, Any]
        Payload data to encode in the token (e.g., {"sub": username}).
    expires_delta : Optional[timedelta], optional
        Token expiration duration. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns
    -------
    str
        Encoded JWT token as a string.

    Raises
    ------
    TypeError
        If jwt.encode returns a non-string value unexpectedly.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if not isinstance(encoded_token, str):
        raise TypeError(
            f"Expected string from jwt.encode, got {type(encoded_token).__name__}"
        )
    return encoded_token


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, str]:
    """Validate JWT and return user claims."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
        return {"username": username, "token": token}
    except JWTError:
        raise credentials_exception
