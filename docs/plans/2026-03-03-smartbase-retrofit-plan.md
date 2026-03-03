# SmartBase Retrofit + Workflow Implementation Plan

**Date:** 2026-03-03
**Spec source:** `~/Downloads/admin-smartbase-retrofit.md`
**Branch strategy:** `fix/smartbase-retrofit` off `main`

---

## Diagnosis Summary

Six confirmed breaks in the admin surface after the Unfold→SmartBase migration:

| Break | File | Problem |
|-------|------|---------|
| BREAK-1 | `templates/admin/index.html` | Includes `unfold/helpers/site_branding.html` (not installed); context vars never injected by SmartBase |
| BREAK-2 | `templates/admin/applications/application/change_form.html` | Uses Unfold blocks (`form_top`, `after_field_sets`); also extends `admin/change_form.html` instead of `sb_admin/actions/change_form.html` |
| BREAK-3 | `templates/unfold/helpers/search.html` | Dead Unfold leftover |
| BREAK-4 | Two competing dashboards | `admin/index.html` (broken) vs `stats_widget.html` (working) |
| BREAK-5 | `change_form.html` inline styles | Hardcoded `background: white; color: #111` — no dark mode |
| BREAK-6 | `admin_shortcuts.js` | Targets `select[name="status"]` — needs verification in SmartBase DOM |

### Critical Template Discovery

SmartBase sets `change_form_template = "sb_admin/actions/change_form.html"` on its base ModelAdmin class. The project override at `templates/admin/applications/application/change_form.html` extends `admin/change_form.html` (Django default), NOT SmartBase's template. This means:

- The summary card and timeline render inside Django's default admin layout
- SmartBase replaces this entirely with its own template
- **Result:** Summary card + timeline were never visible in SmartBase, even ignoring the Unfold block names

**Fix:** Set `change_form_template` on `ApplicationAdmin` to point to our custom template, which extends `sb_admin/actions/change_form.html`.

### SmartBase Block Names (confirmed from source)

| Purpose | SmartBase Block | Old Unfold Block |
|---------|----------------|-----------------|
| Full page content | `content` | `content` |
| Form element + fields | `form` | `form_top` / `after_field_sets` |
| After fieldsets (scripts) | `admin_change_form_document_ready` | `after_field_sets` |
| Extra JS after main bundle | `additional_js` | `extrajs` |
| Page title | `title` | `title` |
| Extra head content | `extrahead` | `extrahead` |

---

## Execution Order

Fix breaks first (Tasks 1-4), then features (Tasks 5-9). Run `manage.py check` after each task.

### Phase A: Fix Breaks (Tasks 1-4)

#### TASK-1: Purge Unfold References

**Files changed:**
- DELETE `templates/admin/index.html`
- DELETE `templates/unfold/` (entire directory)

**Why:** `index.html` includes non-existent `unfold/helpers/site_branding.html` and uses context variables SmartBase never provides. Dashboard already works via `DashboardStatsWidget` → `stats_widget.html`.

**Verify:** `manage.py check` + visit `/admin/` → dashboard renders from `stats_widget.html`.

#### TASK-2: Rewrite change_form.html for SmartBase

**Files changed:**
- REWRITE `templates/admin/applications/application/change_form.html`
  - Extends `sb_admin/actions/change_form.html` (not `admin/change_form.html`)
  - Uses `{% block content %}` with `{{ block.super }}` sandwich pattern
  - Summary card BEFORE `{{ block.super }}`, timeline AFTER
  - Tailwind `dark:` variants instead of inline styles
  - JS via `{% block additional_js %}` (not `extrajs`)
- EDIT `applications/admin.py` — set `change_form_template` on `ApplicationAdmin`:
  ```python
  change_form_template = "admin/applications/application/change_form.html"
  ```
- CREATE `templates/admin/partials/_status_badge.html` (reusable badge partial)

**Why:** Current template extends wrong base, uses wrong block names, has inline styles that break dark mode.

**Verify:** Open any application at `/admin/applications/application/<pk>/change/`. Summary card visible above form. Timeline visible below form. Dark mode works.

#### TASK-3: Verify Dashboard Context Wiring

**Files changed:** Likely none — verification only.

**Steps:**
1. Confirm `DashboardStatsWidget.get_widget_context_data(self, request)` signature matches SmartBase parent
2. Verify `stats_widget.html` Tailwind classes (`mb-24`, `p-16`, `gap-16`) are in compiled CSS
3. If classes missing, run `tailwind build` — these are standard Tailwind values (mb-24 = 6rem)

**Verify:** Dashboard shows greeting, status cards, queue health, recent submissions table.

#### TASK-4: Verify Keyboard Shortcuts

**Files changed:** `static/js/admin_shortcuts.js` (only if selector needs updating)

**Steps:**
1. On a live change form, inspect DOM for `select[name="status"]`
2. If element exists with that name → shortcuts work as-is
3. If SmartBase wraps it differently → update selector to `.field-status select` or `[data-field-name="status"] select`
4. Confirm STATUS_MAP values match model: `received`, `under_review`, `needs_more_info`, `approved`, `declined`

**Verify:** Press Ctrl+Shift+R on change form → status select updates, green flash + toast.

---

### Phase B: Branding + Features (Tasks 5-9)

#### TASK-5: GCLBA Branding

**Files changed:**
- CREATE `static/sb_admin/css/gclba_theme.css` — GCLBA green accent overrides
- Inject CSS via SmartBase's `{% block extrahead %}` or `{% block style_init %}` — need to confirm which block is available for a project-level base override
- Add favicon `<link>` to GCLBA diamond icon
- EDIT `config/sbadmin_config.py` — add Review Queue nav item (prep for TASK-6)

**Note on CSS injection:** SmartBase's base template is `sb_admin/sb_admin_base_no_sidebar.html`. We can override at project level and inject `gclba_theme.css` in `{% block extrahead %}`. But since SmartBase uses its own template path (`sb_admin/`), the override goes in `templates/sb_admin/sb_admin_base_no_sidebar.html`.

**Verify:** Login shows GCLBA branding. Primary buttons green. Favicon is GCLBA diamond.

#### TASK-6: Review Workflow Queue

**Files created:**
- `applications/views/review_queue.py` — `review_queue`, `review_application`, `review_update_status` views
- `templates/admin/review_queue/review.html` — full page wrapper
- `templates/admin/review_queue/_panel.html` — HTMX swap target
- `templates/admin/review_queue/empty.html` — empty state

**Files edited:**
- `config/urls.py` — add `/admin/review/` routes BEFORE `sb_admin_site.urls`

**Priority ordering:** Unassigned received → assigned to me (received) → assigned to me (under review). Oldest first within each group.

**Verify:** `/admin/review/` redirects to first app or shows empty. HTMX swap on "Update & Next".

#### TASK-7: Inline Claim Button + Pending Badge

**Files created:**
- `applications/views/admin_api.py` — `assign_to_me`, `pending_count` endpoints

**Files edited:**
- `applications/admin.py` — add `claim_action` display method to `ApplicationAdmin`
- `config/urls.py` — add `/admin/api/assign/<pk>/` and `/admin/api/pending/` routes

**Verify:** List view shows "Claim" button for unassigned apps. Click claims via HTMX. Sidebar badge polls every 60s.

#### TASK-8: Document Review Panel (Alpine.js)

**Files created:**
- `templates/admin/partials/_document_review_panel.html` — Alpine.js OK/Flag/Pending buttons per document

**Files edited:**
- `applications/models.py` — add `document_review = JSONField(default=dict, blank=True)`
- `applications/views/admin_api.py` — add `save_document_review` endpoint
- `config/urls.py` — add `/admin/api/doc-review/<pk>/` route
- Migration auto-generated

**Alpine.js dependency:** Check if SmartBase bundles Alpine. If not, add CDN script to base override from TASK-5.

**Verify:** Document review buttons appear on change form. OK/Flag/? toggles save via fetch POST.

#### TASK-9: Age Column + List Polish

**Files edited:**
- `applications/admin.py` — verify `submitted_age` method exists (already confirmed at line 771), add color-coded pill styling, update `ordering`

**Already exists:** `submitted_age` at admin.py:771, `display_assignee` at admin.py:765.

**Verify:** Age column shows green/amber/red pills. Default sort newest-first.

---

## Commit Strategy

| Commit | Tasks | Message |
|--------|-------|---------|
| 1 | TASK-1 | `fix(admin): remove broken Unfold templates, clean dead index.html` |
| 2 | TASK-2 + TASK-4 | `fix(admin): rewrite change_form for SmartBase blocks, add status badge partial` |
| 3 | TASK-3 | `fix(admin): verify dashboard context wiring, fix Tailwind spacing if needed` |
| 4 | TASK-5 | `feat(admin): add GCLBA green accent branding to SmartBase chrome` |
| 5 | TASK-6 | `feat(admin): add review workflow queue with HTMX navigation` |
| 6 | TASK-7 | `feat(admin): inline claim button + pending badge with HTMX polling` |
| 7 | TASK-8 | `feat(admin): document review panel with Alpine.js + JSONField` |
| 8 | TASK-9 | `feat(admin): color-coded age column, ordering polish` |

---

## Risk Notes

1. **SmartBase CSS conflicts** — SmartBase ships its own Tailwind. Our `stats_widget.html` and `change_form.html` Tailwind classes must be present in either SmartBase's bundle OR our compiled CSS. May need to run `tailwind build` to include admin-template classes.

2. **Alpine.js availability** — SmartBase may not bundle Alpine. Verify before building TASK-8. Fallback: CDN script tag in base override.

3. **HTMX CSRF** — SmartBase base template already sets `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on `<body>`. Our HTMX endpoints should get CSRF automatically. Verify.

4. **Template resolution order** — Django resolves templates by DIRS first, then installed app template dirs. Our `templates/` dir (in DIRS) takes priority over SmartBase's `sb_admin/` templates. Override filenames must match SmartBase's paths exactly when extending.
