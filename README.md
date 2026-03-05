# GCLBA Application Portal

Property purchase portal for the Genesee County Land Bank Authority (GCLBA).

## Current App Surfaces

- Buyer application flow: `/apply/`
- Staff admin and review tools: `/admin/`
- Staff review queue: `/admin/review/`

## Current Feature Set

- Property-first accordion application flow (HTMX + server-rendered templates)
- Program support:
  - Featured Homes
  - Ready for Rehab
  - VIP Spotlight
  - Vacant Lot is present in metadata but intentionally disabled
- Draft save/resume with magic-link email (`/apply/save/`, `/apply/resume/<token>/`)
- Conditional document requirements by program and purchase type
- VIP multi-file uploads for portfolio photos and support letters
- Eligibility disqualification gate before full submission
- Draft-to-submission conversion with typed `Document` rows
- Buyer confirmation email + staff new-submission email on submit
- Staff review queue with auto-claim and "update and next" workflow
- Admin assignment endpoint, pending-count endpoint, and per-document review status API
- Status transition audit trail (`StatusLog`) with transition validation
- Buyer status emails on:
  - `needs_more_info`
  - `approved`
  - `declined`
- Required note enforcement for:
  - `needs_more_info`
  - `declined`

## Tech Stack

- Python 3.13
- Django 6.0.2
- `django-smartbase-admin` (admin UI layer)
- HTMX + Alpine.js
- Tailwind CSS (built via `django-tailwind` + Node toolchain)
- PostgreSQL in production (`DATABASE_URL`), SQLite locally by default
- WhiteNoise for static files
- `django-anymail` (Resend backend option) for outbound email
- `django-storages` for S3-compatible media storage in production

## Key App Components

```text
applications/
  admin.py                    # SmartBase admin registrations, actions, filters
  admin_utils.py              # Dashboard widget helpers
  models.py                   # User, Property, ApplicationDraft, Application, Document, StatusLog
  status_notifications.py     # Buyer-status email + transition-note rules
  csv_import.py               # CSV/Excel import logic for Property inventory
  views/
    accordion.py              # Main /apply/ accordion flow
    submission.py             # Draft -> Application conversion + submit emails
    review_queue.py           # /admin/review/* workflow
    admin_api.py              # assign/pending/doc-review/admin import endpoints
    documents.py              # Staff-only document access

config/
  settings.py                 # Runtime config (DB, email, storage, security)
  urls.py                     # Root routes
  sbadmin_config.py           # SmartBase menu + dashboard config

templates/
  apply/                      # Buyer flow templates
  admin/review_queue/         # Staff queue templates
  emails/                     # Outbound email templates
```

## Data Model (Primary)

- `ApplicationDraft`: in-progress JSON-backed draft with 14-day expiry token
- `Application`: submitted record used for staff filtering/review
- `Document`: uploaded file metadata per application
- `StatusLog`: immutable audit log of status transitions
- `Property`: searchable inventory used by property picker/autocomplete
- `User`: custom auth model (`AUTH_USER_MODEL=applications.User`)

## Local Development

### 1. Prerequisites

- Python 3.13+
- Node.js (required for Tailwind build)

### 2. Install Python Dependencies

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

For lint/test tooling:

```bash
pip install -r requirements/development.txt
```

### 3. Install Frontend Dependencies and Build CSS

```bash
npm --prefix theme/static_src install
./venv/bin/python manage.py tailwind build
```

### 4. Configure Environment

Create `.env` in repo root:

```env
DJANGO_SECRET_KEY=dev-only-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:8199,http://127.0.0.1:8199
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=applications@thelandbank.org
STAFF_NOTIFICATION_EMAIL=offers@thelandbank.org
RESEND_API_KEY=
```

### 5. Migrate and Run

```bash
./venv/bin/python manage.py migrate
./venv/bin/python manage.py createsuperuser
./venv/bin/python manage.py runserver 8199
```

Open:

- Buyer: `http://127.0.0.1:8199/apply/`
- Admin: `http://127.0.0.1:8199/admin/`

## Useful Commands

```bash
./venv/bin/python manage.py check
./venv/bin/python manage.py makemigrations --check
./venv/bin/python manage.py test
ruff check .
```

Property import commands:

```bash
./venv/bin/python manage.py import_properties path/to/file.csv
./venv/bin/python manage.py import_properties path/to/file.xlsx --replace --batch "March 2026"
./venv/bin/python manage.py import_fm_csv featured_homes path/to/filemaker.csv --replace
```

## Status Workflow

Statuses:

- `received`
- `under_review`
- `needs_more_info`
- `approved`
- `declined`

Allowed transitions:

- `received -> under_review`
- `under_review -> approved|declined|needs_more_info`
- `needs_more_info -> under_review`
- `declined -> under_review` (re-open allowed)
- `approved` is terminal

## Deployment Notes

- Deployment scripts currently run:
  1. Node install for Tailwind assets
  2. `python manage.py tailwind build`
  3. `python manage.py collectstatic --noinput`
  4. `python manage.py migrate --noinput`
  5. `python manage.py ensure_superuser`
  6. `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3`
- These commands are defined in:
  - `Procfile`
  - `nixpacks.toml`
  - `railpack.json`
- `ensure_superuser` currently creates/resets username `Admin` with password `Admin123` unless that command is changed.

## Key Environment Variables (Production)

- `DATABASE_URL`
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `EMAIL_BACKEND`
- `RESEND_API_KEY`
- `DEFAULT_FROM_EMAIL`
- `STAFF_NOTIFICATION_EMAIL`
- Optional S3-compatible media storage:
  - `AWS_STORAGE_BUCKET_NAME` (or `AWS_S3_BUCKET_NAME`)
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_S3_REGION_NAME` (or `AWS_DEFAULT_REGION`)
  - `AWS_S3_ENDPOINT_URL`
  - `AWS_S3_CUSTOM_DOMAIN`

## Troubleshooting

### `ModuleNotFoundError: No module named 'django'`

Install dependencies into the active environment:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `RuntimeError: DJANGO_SECRET_KEY must be set in production`

Expected when `DJANGO_DEBUG=False` and `DJANGO_SECRET_KEY` is not set.

### Missing CSS / broken styling

Rebuild Tailwind output:

```bash
npm --prefix theme/static_src install
./venv/bin/python manage.py tailwind build
```

### Status change blocked in admin

`needs_more_info` and `declined` require a staff note.

### Buyer emails not sending

Check:

- `EMAIL_BACKEND`
- `RESEND_API_KEY` (if using Resend backend)
- `DEFAULT_FROM_EMAIL`
