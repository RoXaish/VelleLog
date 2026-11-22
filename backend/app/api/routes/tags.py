from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CsrfProtectedUser, CurrentUser
from app.db.session import get_db
from app.models.tag import Tag, journal_entry_tags
from app.schemas.tag import TagCreate, TagResponse, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


def _get_owned_tag(db: Session, tag_id: int, user_id: int) -> Tag:
    tag = db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    ).scalar_one_or_none()

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return tag


def _name_taken(
    db: Session,
    user_id: int,
    name: str,
    exclude_tag_id: int | None = None,
) -> bool:
    statement = select(Tag.id).where(
        Tag.user_id == user_id,
        func.lower(Tag.name) == name.lower(),
    )
    if exclude_tag_id is not None:
        statement = statement.where(Tag.id != exclude_tag_id)
    return db.execute(statement).scalar_one_or_none() is not None


def _entry_count(db: Session, tag_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(journal_entry_tags)
        .where(journal_entry_tags.c.tag_id == tag_id)
    ).scalar_one()


def _tag_response(tag: Tag, entry_count: int) -> TagResponse:
    return TagResponse.model_validate(tag).model_copy(
        update={"entry_count": entry_count}
    )


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal tag",
)
def create_tag(
    payload: TagCreate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> TagResponse:
    """Create a tag owned by the authenticated user."""
    if _name_taken(db, current_user.id, payload.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with that name already exists",
        )

    tag = Tag(user_id=current_user.id, name=payload.name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with that name already exists",
        ) from None

    db.refresh(tag)
    return _tag_response(tag, 0)


@router.get(
    "",
    response_model=list[TagResponse],
    summary="List the authenticated user's tags",
)
def list_tags(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[TagResponse]:
    """Return all tags owned by the current user with usage counts."""
    rows = db.execute(
        select(Tag, func.count(journal_entry_tags.c.journal_entry_id))
        .outerjoin(journal_entry_tags, journal_entry_tags.c.tag_id == Tag.id)
        .where(Tag.user_id == current_user.id)
        .group_by(Tag.id)
        .order_by(func.lower(Tag.name), Tag.id)
    ).all()

    return [
        _tag_response(tag, int(entry_count))
        for tag, entry_count in rows
    ]


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Rename a personal tag",
)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> TagResponse:
    """Rename a tag owned by the authenticated user."""
    tag = _get_owned_tag(db, tag_id, current_user.id)

    if _name_taken(
        db,
        current_user.id,
        payload.name,
        exclude_tag_id=tag.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with that name already exists",
        )

    tag.name = payload.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with that name already exists",
        ) from None

    db.refresh(tag)
    return _tag_response(tag, _entry_count(db, tag.id))


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a personal tag",
)
def delete_tag(
    tag_id: int,
    current_user: CsrfProtectedUser,
    db: Session = Depends(get_db),
) -> Response:
    """Delete a tag owned by the current user without deleting its entries."""
    tag = _get_owned_tag(db, tag_id, current_user.id)
    db.delete(tag)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
