# County Landing - Home Sales Application Portal

## Overview
Digital application process for County Landing's home sales team. Replaces manual/paper application workflow with a web-based system for applicants and a management dashboard for the sales team.

## Tech Stack
Python, Django, Django REST Framework, HTMX, Django Unfold

## Architecture
- **Admin (sales team)**: Django Unfold — modern admin theme with sidebar nav, colored status badges, dark mode
- **Public (applicants)**: HTMX + Django templates — interactive forms without page reloads, progressive enhancement
- **API (future)**: Django REST Framework — if mobile app or external integrations needed later

## Project Structure
```
county-landing-app/
├── config/           # Django settings, URLs, WSGI/ASGI, utils
├── applications/     # Core app: Application, Document, ApplicationNote models
├── templates/        # HTML templates (full pages + HTMX partials)
├── static/           # CSS, JS, images
├── media/            # User-uploaded files (gitignored)
├── .claude/          # Claude Code skills and hooks
│   ├── settings.json # Quality gate hooks
│   └── skills/       # django-models, django-forms, htmx-patterns,
│                     # pytest-django-patterns, systematic-debugging
└── pyproject.toml    # Ruff + pytest config
```

## Development Commands
```bash
# Activate virtual environment
source venv/bin/activate

# Run dev server
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Testing
pytest
pytest -x --lf           # Stop first, last failed
pytest --cov=applications # With coverage

# Linting & Formatting
ruff format .
ruff check .
ruff check --fix .
```

## Dev Credentials
- Admin: `admin` / `admin123` (dev only)
- Admin URL: http://127.0.0.1:8000/admin/

## Current Status

| Item | Status |
|------|--------|
| Django project scaffold | Done |
| Application/Document/Note models | Done |
| Admin interface (Unfold) | Done |
| HTMX + django-htmx integration | Done |
| Django skills (models, forms, htmx, testing, debugging) | Done |
| Quality gate hooks (Ruff, branch protection, auto-test) | Done |
| Git repo initialized | Done |
| Public application form | Not started |
| Sales team dashboard | Not started |
| Email notifications | Not started |
| Specs from boss | Waiting |

## Recent Decisions

| Decision | Why | Date |
|----------|-----|------|
| Django 6.0 + DRF | Full-stack framework with built-in admin, auth, ORM; DRF for future API | 2026-02-19 |
| HTMX over React/Next.js for MVP | Single codebase, faster to build, perfect for form-heavy workflow; DRF ready if API needed later | 2026-02-19 |
| Django Unfold for admin | Modern admin UI for sales team; colored status badges, sidebar nav, dark mode | 2026-02-19 |
| Ruff over Black+flake8+isort | Single Rust-based tool replaces 4 Python tools, much faster | 2026-02-19 |
| SQLite for dev, PostgreSQL for prod | Zero-config dev; env vars switch DB engine | 2026-02-19 |
| `config` as project package name | Cleaner than `county_landing_app`; convention from claude-code-django | 2026-02-19 |
| Skills from claude-code-django | Django models, forms, htmx, testing, debugging patterns for Claude Code | 2026-02-19 |
| Green primary color in Unfold | Professional, fresh look for sales portal | 2026-02-19 |

## Architecture Notes
- **Fat models, thin views**: Business logic in models (see django-models skill)
- **Status workflow**: Draft -> Submitted -> Under Review -> Approved/Denied/Withdrawn
- **HTMX partials**: `_partial.html` naming convention; detect with `request.htmx`
- **CSRF for HTMX**: `hx-headers` on `<body>` tag — all requests protected automatically
- **`assigned_to` field**: Links applications to sales team members (Django User model)
- **Document uploads**: Organized by date in `media/applications/YYYY/MM/`
- **ApplicationNote**: Internal team comments, separate from applicant-facing notes

## Next Steps
1. Wait for specs from boss
2. Build public application form (HTMX multi-step form)
3. Build sales team dashboard (custom views beyond admin)
4. Set up email notifications (application status changes)
5. Add document upload flow for applicants
