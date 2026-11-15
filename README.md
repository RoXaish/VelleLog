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
│   │   │   └── config.py        # Typed application settings (Pydantic Settings)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # SQLAlchemy 2.x DeclarativeBase
│   │   │   └── session.py       # Engine, foreign key listener, and SessionLocal factory
│   │   ├── models/              # ORM models (reserved for subsequent milestones)
│   │   ├── schemas/             # Pydantic schemas (reserved for subsequent milestones)
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── router.py        # Top-level API router
│   │       └── routes/
│   │           ├── __init__.py
│   │           └── health.py    # Health check endpoint
│   │
│   ├── alembic/
│   │   ├── env.py               # Alembic environment (dynamic URL, SQLite batch mode)
│   │   ├── script.py.mako
│   │   └── README
│   ├── alembic.ini              # Alembic configuration
│   ├── pytest.ini               # Pytest configuration
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Pytest fixtures (TestClient, isolated database session)
│   │   ├── test_health.py       # GET /api/health endpoint test
│   │   └── test_db.py           # SQLite foreign keys & session dependency tests
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

Default contents:
```env
PROJECT_NAME="Velle Log"
ENV="development"
DATABASE_URL="sqlite:///./vellelog.db"
```

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

The suite currently contains 6 tests: the health endpoint, SQLite connectivity, foreign-key enforcement, invalid foreign-key rejection, session lifecycle handling, and development database isolation. No database migrations (revisions) exist yet because no ORM models have been defined.

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

> **Scope note:** Milestone 1 establishes the project foundation only. The showcase data on the frontend is illustrative. Authentication, friend groups, weekly schedule entry, availability computation, and database models are not implemented yet and will arrive in later milestones.
