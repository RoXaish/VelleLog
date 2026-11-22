from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, verify_csrf
from app.core.cookies import (
    AUTH_COOKIE_NAME,
    clear_auth_cookies,
    generate_csrf_token,
    set_auth_cookies,
)
from app.core.security import hash_password, verify_password_or_dummy
from app.core.tokens import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Create a user account with a normalized email and Argon2 password hash.
    Password material is never returned.
    """
    existing_user_id = db.execute(
        select(User.id).where(User.email == payload.email)
    ).scalar_one_or_none()

    if existing_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        # Covers races between the existence check and insert. The unique
        # index remains the source of truth; internal details stay hidden.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None

    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive an access token",
)
def login_user(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email and password.

    The browser session is established with HttpOnly and CSRF cookies. The
    response body still returns the access token for non-browser API clients.

    Unknown emails and incorrect passwords intentionally produce the same
    generic error so account existence is not revealed.
    """
    user = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()

    password_hash = user.password_hash if user is not None else None
    if not verify_password_or_dummy(payload.password, password_hash) or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    set_auth_cookies(response, access_token, generate_csrf_token())
    return TokenResponse(access_token=access_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the browser authentication cookies",
)
def logout_user(request: Request) -> Response:
    """
    End a cookie-based session.

    Requests that carry an auth cookie must also prove CSRF possession via the
    double-submit header. Bearer-only clients receive no cookies to clear.
    """
    if AUTH_COOKIE_NAME in request.cookies:
        verify_csrf(request)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
)
def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Return the public profile for the bearer token's user.

    Requires a valid access token; password material is never included.
    """
    return UserResponse.model_validate(current_user)
