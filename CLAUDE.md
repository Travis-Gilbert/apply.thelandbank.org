# GCLBA Application Portal

## Overview
Digital property purchase application portal for the Genesee County Land Bank Authority (GCLBA). Replaces the manual PDF/email workflow with a web-based 8-step form for buyers and a Django Unfold admin dashboard for staff review. Production URL: apply.thelandbank.org

**Stakeholder**: Alex Riley, Director — GCLBA

## Tech Stack
Python 3.13, Django 6.0, Django REST Framework, HTMX, Django Unfold, Tailwind CSS (CDN)

## Architecture
- **Staff dashboard**: Django Unfold — colored status badges, organized fieldsets, inline documents, audit trail
- **Buyer form**: HTMX + Django templates — 8-step multi-step form with conditional logic, progressive enhancement
- **API (future)**: Django REST Framework — if mobile app or external integrations needed later

## Project Structure
```
county-landing-app/
├── config/              # Django settings, URLs, WSGI/ASGI, utils
├── applications/        # Core app: models, views, forms, admin
│   ├── models.py        # ApplicationDraft, Application, Document, StatusLog
│   ├── views.py         # 8 step views + save/resume + submission
│   ├── forms.py         # Step1-8 form classes
│   ├── admin.py         # Unfold admin with status badges + audit trail
│   └── urls.py          # /apply/ routes
├── templates/
│   ├── base.html        # Tailwind CDN + HTMX + GCLBA header/footer
│   └── apply/           # 12 templates (steps, confirmation, disqualified, etc.)
├── static/              # CSS, JS, images
├── media/               # Uploaded documents (gitignored)
│   ├── drafts/<token>/  # Temp uploads during form completion
│   └── applications/    # Final uploads organized by YYYY/MM/
├── .claude/             # Claude Code skills and hooks
└── pyproject.toml       # Ruff + pytest config
```

## Development Commands
```bash
source venv/bin/activate
python manage.py runserver              # Dev server on :8000
python manage.py makemigrations && python manage.py migrate
pytest                                  # Run tests
ruff format . && ruff check --fix .     # Format + lint
```

## Dev Credentials
- Admin: `admin` / `admin123` (dev only)
- Admin URL: http://127.0.0.1:8000/admin/
- Buyer form: http://127.0.0.1:8000/apply/

## Current Status

| Item | Status |
|------|--------|
| Django project scaffold | Done |
| 4 models (Draft, Application, Document, StatusLog) | Done |
| Unfold admin with status badges + audit trail | Done |
| 8-step buyer form (all templates + views) | Done |
| Conditional steps (6: rehab, 7: land contract) | Done |
| Eligibility gate (Step 4 hard block) | Done |
| Document uploads (conditional on purchase type) | Done |
| Save-and-return magic links | Done |
| Email notifications (buyer + staff, console backend) | Done |
| Confirmation page with reference number | Done |
| Disqualification page | Done |
| Tailwind CDN + GCLBA branding | Done |
| HTMX + django-htmx integration | Done |
| Ruff + quality gate hooks | Done |
| Tests | Not started |
| Production deployment (Railway) | Not started |
| Real email backend (SendGrid/Resend) | Not started |
| Custom staff dashboard beyond admin | Not started |

## Application Flow

```
Buyer visits /apply/
  ├── Step 1: Identity (name, email, phone, address)
  ├── Step 2: Property (address, parcel, program type)
  ├── Step 3: Offer (amount, purchase type, intended use)
  ├── Step 4: Eligibility gate ──→ [disqualified] if taxes/foreclosure
  ├── Step 5: Documents (conditional on purchase type)
  ├── Step 6: Rehab plan (only if Ready for Rehab) ← CONDITIONAL
  ├── Step 7: Land contract (only if land contract) ← CONDITIONAL
  └── Step 8: Acknowledgments → SUBMIT
        ├── Creates Application + Documents
        ├── Generates GCLBA-YYYY-NNNN reference
        ├── Emails buyer confirmation
        ├── Emails staff notification
        └── Shows confirmation page

Save & Resume:
  ├── "Save Progress" button → sends magic link email
  └── /apply/resume/<uuid>/ → restores session at current step
```

## Models

| Model | Purpose |
|-------|---------|
| ApplicationDraft | UUID token, JSONField form_data, step tracking, 14-day expiry |
| Application | Flat fields for all 8 sections, reference_number, status workflow |
| Document | Typed uploads (photo_id, pay_stubs, bank_statement, proof_of_funds, preapproval) |
| StatusLog | Audit trail — auto-created on status change in admin |

## Recent Decisions

| Decision | Why | Date |
|----------|-----|------|
| Django 6.0 + DRF | Full-stack framework with built-in admin, auth, ORM | 2026-02-19 |
| HTMX over React/Next.js | Single codebase, faster to build, form-heavy workflow | 2026-02-19 |
| Django Unfold for admin | Modern admin UI for staff; status badges, sidebar, dark mode | 2026-02-19 |
| Ruff over Black+flake8+isort | Single Rust-based tool, much faster | 2026-02-19 |
| SQLite for dev, PostgreSQL for prod | Zero-config dev; env vars switch DB engine | 2026-02-19 |
| Tailwind CDN for MVP | No build step; switch to compiled for production | 2026-02-19 |
| Console email for dev | Swap to SendGrid/Resend for production | 2026-02-19 |
| ApplicationDraft + JSONField | Multi-step form storage; flat fields on Application for admin | 2026-02-19 |
| UUID tokens for magic links | Prevents enumeration; enables save-and-return | 2026-02-19 |
| No tests tonight | Ship working MVP; add tests in next session | 2026-02-19 |

## Architecture Notes
- **Fat models, thin views**: Business logic in models (see django-models skill)
- **Status workflow**: Submitted → Under Review → Docs Requested → Approved/Denied/Withdrawn
- **Conditional steps**: Steps 6 (rehab) and 7 (land contract) skip based on program_type/purchase_type
- **Eligibility gate**: Step 4 hard-blocks if delinquent taxes or tax foreclosure
- **CSRF for HTMX**: `hx-headers` on `<body>` tag — all requests protected automatically
- **Document types**: Conditional on purchase_type (cash→proof_of_funds, land_contract→pay_stubs+bank, conventional→preapproval)
- **Reference numbers**: GCLBA-YYYY-NNNN, auto-generated on submission

## Next Steps
1. Full walkthrough testing (min path: cash buyer, max path: rehab + land contract)
2. Add pytest suite
3. Production deployment (Railway + PostgreSQL + S3)
4. Real email backend (SendGrid or Resend)
5. Custom staff dashboard beyond admin
6. File size/type validation on uploads
