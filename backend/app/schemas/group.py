from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
)


def _normalize_name(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_invite_code(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


GroupName = Annotated[
    str,
    BeforeValidator(_normalize_name),
    Field(min_length=1, max_length=100),
]

InviteCode = Annotated[
    str,
    BeforeValidator(_normalize_invite_code),
    Field(min_length=1, max_length=32),
]


class GroupCreate(BaseModel):
    """Payload to create a new group circle."""

    name: GroupName


class GroupJoin(BaseModel):
    """Payload to join an existing group circle via invite code."""

    invite_code: InviteCode


class GroupMemberUser(BaseModel):
    """Public representation of a user associated with a membership."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class GroupMemberResponse(BaseModel):
    """Representation of a group member."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: str
    joined_at: datetime
    user: GroupMemberUser

    @computed_field
    @property
    def email(self) -> EmailStr:
        return self.user.email


class GroupResponse(BaseModel):
    """Basic representation of a group circle."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    invite_code: str
    owner_id: int
    created_at: datetime


class GroupDetailResponse(BaseModel):
    """Detailed group circle representation including members."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    invite_code: str
    owner_id: int
    created_at: datetime
    members: list[GroupMemberResponse] = Field(validation_alias="memberships")
