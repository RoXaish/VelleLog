from typing import Literal

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT access token response. Never contains user password material."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
