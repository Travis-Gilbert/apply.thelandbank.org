# GCLBA Application Portal

Property purchase application portal for the Genesee County Land Bank Authority (GCLBA), built for two audiences:

- Buyers applying for property programs
- Internal sales staff reviewing and managing submissions

## Surfaces

- Buyer surface: `/apply/`
- Admin surface: `/admin/`

The buyer experience is server-rendered Django templates with HTMX interactions.  
The admin experience uses Django Admin with the Unfold theme and sales-specific workflow customizations.

## Core Features

- Program-specific application paths:
  - Featured Homes
  - Ready for Rehab
  - VIP Spotlight
  - Vacant Lot placeholder (not fully implemented)
- Save and resume via draft token links
- Conditional document requirements by program/purchase type
- Renovation line-item totals for Ready for Rehab
- Staff review workflow with status tracking and audit logs
- Buyer status emails for:
  - Needs More Info
  - Approved
  - Declined
- Admin transition note enforcement for buyer-facing negative transitions

## Tech Stack

- Python 3.13
- Django 6.0.2
- django-unfold
- HTMX
- Tailwind via CDN (no build pipeline)
- PostgreSQL in production (Railway), SQLite locally by default
- WhiteNoise for static files
- django-anymail (Resend) for outbound email

## Project Layout

```text
applications/
  admin.py                    # Admin UX + workflow actions
  admin_utils.py              # Unfold dashboard callbacks/badges
  models.py                   # Application, Draft, Document, StatusLog
  forms/                      # Program-specific forms
  views/                      # Accordion flow, shared steps, submission
  status_notifications.py     # Status-email and note-requirement helpers
  migrations/

config/
  settings.py                 # App config, Unfold, email, DB
  urls.py                     # /apply + /admin routing

templates/
  apply/                      # Buyer templates
  emails/                     # Buyer status-change email templates

CLAUDE.md                     # Detailed product and implementation context
```

## Project Architecture / Structure

### High-Level Request Flow

1. Buyer starts at `/apply/` (accordion flow in `applications/views/accordion.py`).
2. Section submissions validate with Django forms in `applications/forms/*`.
3. Draft progress is stored in `ApplicationDraft.form_data` (JSON) with step tracking.
4. Final submission creates a flat `Application` record plus related `Document` rows.
5. Staff reviews in `/admin/` using Unfold customizations from `applications/admin.py`.
6. Status changes write `StatusLog` and can trigger buyer email notifications.

### Domain Model

- `ApplicationDraft`: in-progress buyer application state
- `Application`: submitted application used by staff for filtering/review
- `Document`: typed upload linked to `Application`
- `StatusLog`: immutable audit trail of status transitions

### Buyer Surface Layers

- Routes: `applications/urls.py`
- Views:
  - `applications/views/accordion.py` (primary flow)
  - `applications/views/shared.py` (legacy shared steps + save/resume helpers)
  - `applications/views/submission.py` (draft-to-application conversion + submit emails)
- Forms:
  - `applications/forms/featured_homes.py`
  - `applications/forms/ready_for_rehab.py`
  - `applications/forms/vip_spotlight.py`
  - `applications/forms/shared.py`
- Templates: `templates/apply/**`

### Admin Surface Layers

- Admin config/actions/filters: `applications/admin.py`
- Dashboard callbacks + sidebar badge counts: `applications/admin_utils.py`
- Status email + transition-note helper logic: `applications/status_notifications.py`
- Email templates:
  - `templates/emails/status_change_needs_more_info.*`
  - `templates/emails/status_change_approved.*`
  - `templates/emails/status_change_declined.*`

### Configuration and Runtime

- App config: `config/settings.py`
- Root routing: `config/urls.py`
- WSGI entrypoint: `config/wsgi.py`
- Deployment command references:
  - `Procfile`
  - `nixpacks.toml`

## Local Development

### 1. Prerequisites

- Python 3.13+
- `pip`

### 2. Install

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` in repo root. Minimal local values:

```env
DJANGO_SECRET_KEY=dev-only-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8199,http://127.0.0.1:8199
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=applications@thelandbank.org
STAFF_NOTIFICATION_EMAIL=offers@thelandbank.org
RESEND_API_KEY=
```

### 4. Database + Run

```bash
./venv/bin/python manage.py migrate
./venv/bin/python manage.py createsuperuser
./venv/bin/python manage.py runserver 8199
```

Open:

- Buyer: `http://127.0.0.1:8199/apply/`
- Admin: `http://127.0.0.1:8199/admin/`

## Validation Commands

```bash
./venv/bin/python manage.py check
./venv/bin/python manage.py makemigrations --check
./venv/bin/python manage.py test
ruff check .
```

## Admin Workflow

### Statuses

- `received`
- `under_review`
- `needs_more_info`
- `approved`
- `declined`

### Rules

- Status changes create `StatusLog` records
- Transition notes are required for:
  - `needs_more_info`
  - `declined`
- Buyer status emails are sent on:
  - `needs_more_info`
  - `approved`
  - `declined`

## Deployment

- Platform: Railway
- Main app URL: `https://apply.thelandbank.org`
- Auto-deploy branch: `main`

Branch flow in this repo:

- `Admin` -> `develop` -> `main`

Typical push command:

```bash
git push origin Admin develop main
```

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

## Additional Context

For full product requirements, program rules, and historical implementation notes, see:

- `CLAUDE.md`

## Troubleshooting

### `python` command not found

Use the venv interpreter directly:

```bash
./venv/bin/python manage.py runserver 8199
```

or activate first:

```bash
source venv/bin/activate
python manage.py runserver 8199
```

### `ModuleNotFoundError: No module named 'django'`

Dependencies are not installed in the active environment:

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### `RuntimeError: DJANGO_SECRET_KEY must be set in production`

Expected when `DJANGO_DEBUG=False` without a secret key.  
Set `DJANGO_SECRET_KEY` in your environment (or `.env`) before startup.

### `No changes detected` vs missing DB columns

If the app complains about missing columns, run migrations in the current environment:

```bash
./venv/bin/python manage.py migrate
```

### Admin status change blocked for missing note

`needs_more_info` and `declined` require `staff_notes`.  
Add a note in the application record, then retry the status update/action.

### Buyer status emails are not being delivered

1. For local development, set:
   - `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`
2. For Resend, confirm:
   - `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`
   - `RESEND_API_KEY` is set
   - `DEFAULT_FROM_EMAIL` is valid for your provider setup

### Static files missing in production

Ensure collectstatic runs during deploy (already in `Procfile` and `nixpacks.toml`), and verify:

- `DEBUG=False`
- `STATIC_ROOT` points to `staticfiles`

### CSRF errors on local or Railway domain

Verify host/origin configuration:

- `DJANGO_ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

Include `http://localhost:8199` for local and deployed domain(s) for production.
