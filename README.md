# Velle Log

**Velle Log** is a web application designed for friend groups to coordinate hangouts effortlessly.

It solves two primary questions:
1. **Who is free right now?**
2. **When can everyone meet?**

Users enter their weekly recurring busy schedules. Members of a group can see each other's availability without exposing private schedule details or calendar labels.

---

## Technology Stack

### Backend
- **Python 3.12+**
- **FastAPI**: Modern, asynchronous web framework for building APIs.
- **Pydantic & Pydantic-Settings**: Data validation and typed environment configuration.
- **SQLAlchemy 2.x**: Modern Python SQL toolkit and Object Relational Mapper (ORM).
- **SQLite**: Local relational database with foreign key enforcement (PostgreSQL-compatible architecture).
- **Alembic**: Database migrations management.
- **Argon2 (`argon2-cffi`)**: Memory-hard password hashing and verification.
- **PyJWT**: Signed JWT access-token creation and validation (HS256).
- **pytest**: Test runner and testing framework with `httpx` / FastAPI `TestClient`.
- **Uvicorn**: Lightning-fast ASGI web server.

### Frontend
- **React 18** with **TypeScript** (strict mode).
- **Vite 5**: Development server and production build tooling.
- **CSS**: Hand-authored design system (no UI framework), cinematic dark palette with warm aurora accents and Inter typography.
- **Accessibility**: Keyboard focus states, semantic landmarks, and full `prefers-reduced-motion` support.

---

## Project Structure

```
VelleLog/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application factory and router registration
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Typed application settings (Pydantic Settings)
│   │   │   ├── security.py      # Argon2 password hashing & verification
│   │   │   └── tokens.py        # JWT access-token creation & validation
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # SQLAlchemy 2.x DeclarativeBase + model registration
│   │   │   └── session.py       # Engine, foreign key listener, and SessionLocal factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── user.py          # User ORM model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── token.py         # TokenResponse schema
│   │   │   └── user.py          # UserCreate / UserLogin / UserResponse schemas
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── deps.py          # Reusable get_current_user auth dependency
│   │       ├── router.py        # Top-level API router
│   │       └── routes/
│   │           ├── __init__.py
│   │           ├── auth.py      # Registration, login & current-user endpoints
│   │           └── health.py    # Health check endpoint
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 489b1fad710a_create_users_table.py
│   │   ├── env.py               # Alembic environment (dynamic URL, SQLite batch mode)
│   │   ├── script.py.mako
│   │   └── README
│   ├── alembic.ini              # Alembic configuration
│   ├── pytest.ini               # Pytest configuration
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Pytest fixtures (TestClient, isolated database session)
│   │   ├── test_health.py       # GET /api/health endpoint test
│   │   ├── test_db.py           # SQLite foreign keys & session dependency tests
│   │   ├── test_security.py     # Argon2 hashing & verification tests
│   │   ├── test_users.py        # User model, constraints & schema tests
│   │   ├── test_migrations.py   # Alembic users table migration test
│   │   ├── test_auth.py         # Registration API tests
│   │   ├── test_login.py        # Login API & credential tests
│   │   ├── test_jwt.py          # JWT creation, claims & validation tests
│   │   └── test_me.py           # Protected /me endpoint & current-user dependency tests
│   ├── requirements.txt         # Backend Python dependencies
│   ├── .env.example             # Example environment configuration (tracked)
│   └── .env                     # Local environment file (git-ignored)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx       # Floating glass navigation & mobile menu
│   │   │   ├── Hero.tsx
│   │   │   ├── ProductPreview.tsx  # Illustrative group availability dashboard
│   │   │   ├── HowItWorks.tsx
│   │   │   ├── FeatureGrid.tsx
│   │   │   └── Footer.tsx
│   │   ├── App.tsx              # App shell, atmosphere, scroll progress & reveal observer
│   │   ├── App.css              # Component and layout styles
│   │   ├── main.tsx
│   │   └── index.css            # Design tokens, atmosphere & motion system
│   ├── index.html               # Document head, metadata & favicon
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── .gitignore
└── README.md
```

---

## Getting Started (Backend)

### 1. Prerequisites
- Python 3.12+ installed on your system.

### 2. Environment Setup
From the project root:

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (CMD):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` if not already present:

```bash
copy .env.example .env   # Windows
# or: cp .env.example .env (Linux/macOS)
```

Contents:
```env
PROJECT_NAME="Velle Log"
ENV="development"
DATABASE_URL="sqlite:///./vellelog.db"

# Required, at least 32 characters. Generate per environment:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET_KEY="replace-with-a-long-random-secret-at-least-32-characters"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"
```

`JWT_SECRET_KEY` has no application default and must be supplied by the environment. The access-token lifetime is configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 30, must be greater than zero). Tokens are signed explicitly with HS256 and validated for signature, expiration, and required `sub`/`exp` claims.

### 4. Running the Development Server
From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The server starts at `http://127.0.0.1:8000`.

- Health check: `http://127.0.0.1:8000/api/health`
- Interactive API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
- Alternative Documentation (ReDoc): `http://127.0.0.1:8000/redoc`

### 5. Running Tests
Run pytest from the `backend` directory:

```bash
pytest -v
```

The suite currently contains 57 tests covering the health endpoint, SQLite connectivity, foreign-key enforcement, session lifecycle, database isolation, Argon2 hashing/verification (including malformed hashes), user creation and unique-email enforcement, password storage, response schema privacy, input validation, the users migration, the registration API, the login/JWT layer (token claims, configured expiration, malformed/expired/unknown-signature rejection, generic 401 errors, and email normalization), and protected access (valid-token `/me` retrieval, subject matching, missing/malformed/expired/tampered tokens, nonexistent users, and password privacy).

### 6. Database Migrations
From the `backend` directory:

```bash
alembic upgrade head   # Apply all migrations
alembic current        # Show the applied revision
```

The development SQLite database is created at `backend/vellelog.db` (git-ignored).

---

## API Reference

Base URL: `http://127.0.0.1:8000/api`

### `POST /api/auth/register`

Create a user account. Emails are trimmed and lowercased; passwords must be 8–128 characters. The password is stored as an Argon2id hash and is never returned.

Request:
```json
{
  "email": "alex@example.com",
  "password": "s3cure-passphrase"
}
```

Response — `201 Created`:
```json
{
  "id": 1,
  "email": "alex@example.com",
  "created_at": "2026-11-15T14:31:07",
  "updated_at": "2026-11-15T14:31:07"
}
```

Errors:
- `409 Conflict` — `{"detail": "Email already registered"}`
- `422 Unprocessable Entity` — invalid email or password format; submitted password values are redacted from validation error details

### `POST /api/auth/login`

Authenticate with email and password. Emails are trimmed and lowercased. Successful responses contain a signed JWT access token; password material is never returned.

Request:
```json
{
  "email": "  Alex@Example.COM  ",
  "password": "s3cure-passphrase"
}
```

Response — `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Errors:
- `401 Unauthorized` — always `{"detail": "Invalid email or password"}` for unknown emails and incorrect passwords (includes `WWW-Authenticate: Bearer`)
- `422 Unprocessable Entity` — invalid request format; submitted password values are redacted

The JWT subject (`sub`) is the user ID; tokens also include `iat` and `exp`. Validation rejects malformed tokens, expired tokens, missing required claims, and unknown signing secrets.

### `GET /api/auth/me`

Return the authenticated user's public profile. Requires a valid access token.

Request header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Response — `200 OK`:
```json
{
  "id": 1,
  "email": "alex@example.com",
  "created_at": "2026-11-15T14:31:07",
  "updated_at": "2026-11-15T14:31:07"
}
```

Errors:
- `401 Unauthorized` — `{"detail": "Could not validate credentials"}` for missing, malformed, expired, or untrusted tokens and tokens whose user no longer exists (includes `WWW-Authenticate: Bearer`)

### `GET /api/health`

Returns `{"status": "ok"}` and remains available without authentication.

---

## Getting Started (Frontend)

### 1. Prerequisites
- Node.js 18+ (verified with Node.js v24.15.0 and npm 11.12.1).

### 2. Environment Setup & Development Server
From the project root:

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 3. Type Checking & Production Build
```bash
# Run TypeScript validation
npm run type-check

# Build for production
npm run build
```

There is no frontend unit test suite yet; TypeScript validation and the production build are the current quality gates.

---

## Current Implementation Status

- [x] **Milestone 1, Part 1: Backend Foundation**
  - [x] FastAPI project layout & architecture
  - [x] SQLAlchemy 2.x configuration with SQLite & foreign key enforcement
  - [x] Environment configuration via Pydantic Settings
  - [x] Unauthenticated `GET /api/health` endpoint returning `{"status": "ok"}`
  - [x] Test suite with FastAPI `TestClient` and database isolation harness

- [x] **Milestone 1, Part 2: Database Migrations & Testing**
  - [x] Alembic initialization and configuration in `backend/`
  - [x] `env.py` configured with `Base.metadata`, dynamic `settings.DATABASE_URL`, and batch SQLite migration support
  - [x] Strengthened test suite (connection test, PRAGMA verification, invalid FK rejection, session lifecycles, dev database isolation)
  - [x] Environment safety and gitignore verification for database files and environment secrets

- [x] **Milestone 1, Part 3: Frontend Foundation & Visual Identity**
  - [x] React + Vite + TypeScript application setup
  - [x] Cinematic dark design system: near-black surfaces, warm aurora (crimson, coral, amber), Inter typography, film grain and vignette
  - [x] Smooth motion layer (scroll reveals, drifting aurora, scroll progress, hover micro-interactions, animated availability timeline) with full `prefers-reduced-motion` support
  - [x] Floating glass navigation, hero, illustrative product preview ("Your group right now" with shared free window), how-it-works steps, and roadmap features
  - [x] Full responsive layout (desktop, tablet, mobile) with zero TypeScript or build errors

- [x] **Milestone 1, Part 4: Final Verification & Git Initialization**
  - [x] Backend test suite passing (6 tests) and live health endpoint verified
  - [x] Frontend type-check and production build verified
  - [x] README updated to reflect the current architecture, setup, and status
  - [x] Git repository initialized at the project root with a curated `.gitignore`

- [x] **Milestone 2, Part 1: Backend Authentication Foundation**
  - [x] `User` ORM model (`id`, unique/indexed `email`, `password_hash`, `created_at`, `updated_at`)
  - [x] Initial Alembic migration creating the `users` table with a unique email index
  - [x] Argon2id `hash_password()` / `verify_password()` utilities with safe handling of invalid hashes
  - [x] `UserCreate` (email + password validation) and `UserResponse` (no password material) schemas
  - [x] Tests-first coverage for creation, uniqueness, hashing, verification, response privacy, and migration schema

- [x] **Milestone 2, Part 2: User Registration API**
  - [x] `POST /api/auth/register` returning `201 Created` with `UserResponse`
  - [x] Email normalization (trim + lowercase) and duplicate detection with `409 Conflict`
  - [x] Pydantic validation errors return `422`; database integrity errors handled safely
  - [x] Password hashing via the existing Argon2 utility; no password material in responses, including sanitized 422 error details
  - [x] Registration tests including success, normalization, duplicates, validation, and password privacy

- [x] **Milestone 2, Part 3: Login API & JWT Authentication**
  - [x] `POST /api/auth/login` with email normalization and Argon2 password verification
  - [x] Generic `401 Unauthorized` responses that do not reveal whether the email or password was wrong
  - [x] HS256 JWT access tokens with user-ID subject, issued-at, and configurable expiration
  - [x] Configuration-driven, minimum-length signing secret with no application default
  - [x] Token validation rejects malformed, expired, incomplete, and unknown-signature tokens

- [x] **Milestone 2, Part 4: Protected Routes & Current User**
  - [x] Reusable `get_current_user` dependency (`CurrentUser` alias) for protected endpoints
  - [x] Bearer token extraction, validation, subject parsing, and database user lookup
  - [x] Generic `401 Unauthorized` with `WWW-Authenticate: Bearer` for all authentication failures
  - [x] `GET /api/auth/me` returns the authenticated user's `UserResponse`
  - [x] Tests for valid, missing, malformed, expired, tampered, and orphaned tokens plus password privacy

> **Scope note:** Milestone 1 establishes the project foundation, and Milestone 2 currently provides authentication fundamentals: user model, registration, login, JWT issuance/validation, and reusable protected-route dependencies with `/api/auth/me`. The showcase data on the frontend is illustrative. Frontend token storage/integration, friend groups, weekly schedule entry, and availability computation are not implemented yet and will arrive in later milestones.
