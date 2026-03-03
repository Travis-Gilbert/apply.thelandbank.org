# GCLBA Application Portal — Comprehensive Improvement Plan

**Date:** 2026-03-02
**Scope:** Full codebase review of buyer surface, admin surface, models, templates, and tests
**Builds on:** docs/design/001–003, docs/ux-qa-2026-02-25/punch-list.md
**Does not duplicate:** P0 admin crash (STORAGES default), P1 hero copy on resume, P1 vertical space — already captured

---

## 1. Critical Fixes (Bugs, Data Integrity, Security)

### 1.1 `full_clean()` never called before `app.save()` at submission

**File:** `applications/views/submission.py:137`
**Impact:** Model-level validators are dead code. `Application.clean()` validates down payment minimum and land contract rules, but `Model.save()` does not run validators by default. All validation relies solely on form-layer checks. If a form bug or future change skips a form validator, corrupted data enters the database silently.

**Fix:** Add `app.full_clean()` before `app.save()` inside the transaction block.

---

### 1.2 `open_house_date` free-text causes `ValueError` crash at submission

**File:** `applications/forms/shared.py:140` / `applications/views/submission.py:87`
**Impact:** The form accepts any string up to 7 characters ("March" passes). Submission calls `date.fromisoformat()` which raises `ValueError`. The bare `except Exception` at submission.py:146 catches it, showing a submission error page for what looked like a successful form fill.

**Fix:** Either change the form field to `DateField(widget=forms.DateInput(attrs={"type": "month"}))` or add `clean_open_house_date()` that parses the expected format and returns a `date` or `None`.

---

### 1.3 `_build_summary` uses wrong key for R4R renovation total

**File:** `applications/views/accordion.py:342`
**Impact:** The collapsed summary bar for R4R line items always shows "Renovation estimate provided" instead of "Estimated total: $X,XXX". The code reads `form_data.get("total_renovation_cost")` but the actual stored key is `"reno_total"`.

**Fix:** Change `"total_renovation_cost"` to `"reno_total"` on line 342.

---

### 1.4 Concurrent submission race condition (double-click creates duplicate Applications)

**File:** `applications/views/accordion.py:727` / `submission.py:136`
**Impact:** Two simultaneous POST requests both read `draft.submitted = False`, both create Application records, both generate distinct reference numbers. The buyer receives two confirmation emails.

**Fix:** Inside the `transaction.atomic()` block in `submit_application()`, add:
```python
draft_locked = ApplicationDraft.objects.select_for_update().get(pk=draft.pk)
if draft_locked.submitted:
    return redirect("applications:confirmation", ref=existing_ref)
```

---

### 1.5 Path traversal risk in `_move_documents`

**File:** `applications/views/submission.py:189`
**Impact:** `source_path` is read from `form_data["uploads"]` JSON and passed directly to `default_storage.open()`. If the JSON blob is ever manipulated (compromised session, bug allowing injection), an attacker could read arbitrary storage paths.

**Fix:** Validate prefix before use:
```python
expected_prefix = f"drafts/{draft.token}/"
if not source_path.startswith(expected_prefix):
    logger.warning("Suspicious source_path in draft %s: %s", draft.token, source_path)
    continue
```

---

### 1.6 No status transition enforcement — any state change is allowed

**File:** `applications/admin.py` / `applications/models.py`
**Impact:** Staff can set RECEIVED → APPROVED (skipping review), or re-open DECLINED → APPROVED. Bulk actions bypass `ApplicationAdminForm.clean()` entirely, so `queryset.update(status=new_status)` changes status with zero validation.

**Fix:** Add `ALLOWED_TRANSITIONS` dict to `Application`:
```python
ALLOWED_TRANSITIONS = {
    "received": {"under_review"},
    "under_review": {"approved", "declined", "needs_more_info"},
    "needs_more_info": {"under_review"},
    "approved": set(),
    "declined": {"under_review"},  # allow re-open
}
```
Validate in `ApplicationAdminForm.clean()` and in `_bulk_set_status()` before applying changes.

---

### 1.7 `document_view` bypasses staff-only guard in dev mode

**File:** `applications/views/documents.py:41`
**Impact:** `FileSystemStorage.url()` returns a public media URL. In dev (`DEBUG=True`), after one staff redirect, the raw URL is accessible to anyone. Not a production issue (S3 uses pre-signed URLs), but a dev hygiene gap.

**Fix:** Check storage type before redirect:
```python
from django.core.files.storage import FileSystemStorage
if not isinstance(default_storage, FileSystemStorage) and hasattr(default_storage, "url"):
    url = default_storage.url(file_path)
    return HttpResponseRedirect(url)
```

---

### 1.8 VIP `NullBooleanField` allows unanswered questions

**File:** `applications/forms/vip_spotlight.py:35–43`
**Impact:** `NullBooleanField(required=False)` accepts `None` as valid. A buyer can submit the VIP proposal without answering Q2 (prior purchases) or Q5 (experience). These are required per the spec.

**Fix:** Convert to `ChoiceField(choices=[("no", "No"), ("yes", "Yes")], widget=RadioSelect)` per CLAUDE.md convention #25, or add explicit `None` check in `clean()`.

---

### 1.9 `section_validate` does not enforce section ordering

**File:** `applications/views/accordion.py:636–650`
**Impact:** A buyer could POST directly to `/apply/section/acks/validate/` with valid acknowledgment data and skip all intermediate sections. The accordion UI makes this unlikely, but the backend should verify sequencing independently.

**Fix:** In `section_validate`, check that `draft.current_step >= section_index` before processing.

---

### 1.10 Rate limiting gaps on `resume_draft` and `section_program_select`

**File:** `applications/views/shared.py:133` / `accordion.py:527`
**Impact:** `resume_draft` accepts unlimited GET requests — an attacker could enumerate UUID tokens. `section_program_select` accepts unlimited POST requests. Both should have rate limits.

**Fix:** Add `@ratelimit(key="ip", rate="10/m")` to `resume_draft` and `@ratelimit(key="ip", rate="20/m")` to `section_program_select`.

---

## 2. Buyer UX Improvements (not in docs/design/002)

### 2.1 Error clearing removes ALL errors on any input event

**File:** `templates/apply/v2/apply_page.html:147–160`
**Impact:** Typing one character in "First Name" clears error messages on "Email" and "Phone" in the same section, before the buyer has fixed those fields.

**Fix:** Scope the error-clearing to the specific field's parent container:
```javascript
var fieldContainer = e.target.closest('.space-y-1, .form-group');
if (fieldContainer) {
    fieldContainer.querySelectorAll('.text-red-600').forEach(el => el.remove());
}
```

---

### 2.2 Progress bar shows "Step 9 of 8" on final step

**File:** `templates/apply/v2/_progress_bar.html:21`
**Impact:** When `completed_count == total_count`, the template renders `Step {{ completed_count|add:1 }} of {{ total_count }}`, showing a step number that exceeds the total.

**Fix:** Guard with `{% if completed_count < total_count %}Step {{ completed_count|add:1 }}{% else %}Complete{% endif %}`.

---

### 2.3 R4R line item inputs are fixed `w-32` on mobile

**File:** `templates/apply/v2/sections/r4r/line_items_expanded.html:37–43`
**Impact:** On a 320px viewport with padding, 128px inputs leave only ~152px for labels. Long trade names ("Garage Repair or Demolition") wrap badly.

**Fix:** Use `w-full sm:w-32` so inputs go full-width on mobile and fixed-width on desktop.

---

### 2.4 Homebuyer education phone numbers are not tappable

**File:** `templates/apply/v2/sections/fh/homebuyer_ed_expanded.html:14–16`
**Impact:** Mobile users cannot tap-to-call. The spec says these are important contacts for required pre-closing education.

**Fix:** Wrap in `<a href="tel:+18107674622">(810) 767-4622</a>`.

---

### 2.5 Program card hover borders don't work on touch devices

**File:** `templates/apply/v2/sections/property_search_expanded.html:183–184`
**Impact:** `onmouseover`/`onmouseout` don't fire on touch. The visual affordance indicating card selection is lost on mobile, which is the primary device for this audience.

**Fix:** Use CSS `:hover` and `:focus-visible` instead of inline JS handlers, or add touch event equivalents.

---

### 2.6 No `hx-sync` on purchase type radios or property search — race conditions

**Files:** `templates/apply/v2/sections/fh/offer_expanded.html:18–22` / `property_search_expanded.html:26–31`
**Impact:** Rapid switching between Cash/Land Contract sends overlapping HTMX requests. The last response to arrive (not the last click) wins, potentially showing wrong fields. Same pattern on property search where 300ms debounce doesn't eliminate the window.

**Fix:** Add `hx-sync="closest form:replace"` on purchase type radios. Add `hx-sync="this:replace"` on the property search input.

---

### 2.7 Non-field errors only rendered in property search section

**File:** Only `property_search_expanded.html` has `{% if form.non_field_errors %}`
**Impact:** Cross-field validation errors in FH offer, R4R offer, VIP proposal, and all other sections are silently swallowed. The buyer sees no error message but the form won't advance.

**Fix:** Add `{% if form.non_field_errors %}` rendering to every `*_expanded.html` template, or extract to a shared include.

---

### 2.8 `resume_draft` silently overwrites in-progress draft

**File:** `applications/views/shared.py:133–151`
**Impact:** If a buyer has one draft in session and clicks an older magic link, the session is silently overwritten with the old draft's token. They lose unsaved work.

**Fix:** Check if a different draft is already in session and show a confirmation before switching:
```python
existing_token = request.session.get("draft_token")
if existing_token and existing_token != str(draft.token):
    return render(request, "apply/confirm_switch_draft.html", {...})
```

---

### 2.9 Magic link email says "Hello," when first name is empty

**File:** `templates/emails/magic_link.html:1`
**Impact:** Before Step 1 (identity), `first_name` is empty. The email renders "Hello," with nothing between greeting and comma.

**Fix:** `Hello{% if first_name %} {{ first_name }}{% endif %},`

---

## 3. Admin UX Improvements (not in docs/design/003)

### 3.1 Dashboard is blank — `SBAdminDashboardView(widgets=[])` has no content

**File:** `config/sbadmin_config.py:49`
**Impact:** Staff land on a blank dashboard page. `admin_utils.py` builds rich statistics (status counts, queue health, stale apps) that are never displayed. This is the first screen staff see.

**Fix:** Wire `get_dashboard_stats()` into SmartBase dashboard widgets, or replace with a custom dashboard template registered to the admin index.

---

### 3.2 Bulk actions bypass state transition validation

**File:** `applications/admin.py:774–839`
**Impact:** Staff selecting 10 applications and clicking "Approve" will approve all of them regardless of current state (including already-declined ones). The `_bulk_set_status` method calls `queryset.update()` directly.

**Fix:** In `_bulk_set_status`, filter the queryset to only applications whose current status is in `ALLOWED_TRANSITIONS[new_status]` (inverse lookup). Skip ineligible applications and report them in the flash message.

---

### 3.3 Assignment changes are not audit-logged

**File:** `applications/admin.py:858–870`
**Impact:** `assign_to_me` and `clear_assignee` use `queryset.update()` which bypasses `save_model()`. No `StatusLog` entry is created for assignment changes. Staff cannot see when an application was assigned or unassigned.

**Fix:** Create `StatusLog` entries in the assign/clear actions similar to `_bulk_set_status`.

---

### 3.4 Email failures in bulk actions not recorded in audit trail

**File:** `applications/admin.py:821–831`
**Impact:** Failed emails increment a counter shown in a flash message, but no durable record exists of which applications had email failures. The next shift won't know.

**Fix:** When email fails, append a note to the `StatusLog.note` field: "Status email failed — manual follow-up needed."

---

### 3.5 `submitted_age` column sorting is counterintuitive

**File:** `applications/admin.py:749`
**Impact:** Clicking the "Age" column header sorts by `submitted_at` ascending (oldest submission date first → actually the most-aged applications). But the Django admin up-arrow implies ascending = smallest, which users expect to mean "1 day" not "90 days".

**Fix:** Change `ordering="submitted_at"` to `ordering="-submitted_at"` so the first click shows oldest (most-aged) first, which matches "highest age" = "most urgent to review".

---

### 3.6 `ApplicationDraftAdmin` exposes full `form_data` JSON

**File:** `applications/admin.py:926–932`
**Impact:** `form_data` is in `readonly_fields` and displays the entire JSON blob including partial PII (address, email, phone, uploaded file paths). For non-superuser staff, this is over-exposure.

**Fix:** Either restrict `form_data` display to superusers only, or render a summary view instead of raw JSON.

---

### 3.7 Concurrent admin save can record wrong `from_status` in audit log

**File:** `applications/admin.py:883`
**Impact:** `form.initial.get("status")` is the status when the form was rendered. If another staff member changes the status between render and save, the audit log records the wrong `from_status`.

**Fix:** Re-read current status from DB inside `save_model`:
```python
current_db_status = Application.objects.values_list("status", flat=True).get(pk=obj.pk)
```

---

## 4. Architecture and Code Quality

### 4.1 `accordion.py` is 1,347 lines — should be split

**File:** `applications/views/accordion.py`
**Impact:** Constants (PROGRAM_META, SECTION_DEFS, SECTION_ORDER), routing helpers, summary builders, context builders, page rendering, four specialized validators, section editing, and render-transition logic all in one file. Hard to navigate, hard to review.

**Recommendation:** Split into:
- `accordion_config.py` — PROGRAM_META, SECTION_DEFS, SECTION_ORDER, `_get_section_order()`, `_resolve_template()`, `_resolve_form_class()`
- `accordion_validators.py` — `_validate_property_search_section()`, `_validate_eligibility_section()`, `_validate_documents_section()`
- `accordion.py` — core views only

---

### 4.2 `doc_labels` dict duplicated in two places

**File:** `accordion.py:709–716` and `accordion.py:982–990`
**Impact:** Identical dictionaries mapping doc type slugs to display names. Any label change requires editing two locations.

**Fix:** Extract to module-level constant `DOC_LABELS` in `shared.py` alongside `_get_required_docs`.

---

### 4.3 FH and R4R acknowledgment forms are byte-for-byte identical

**File:** `forms/featured_homes.py:152–183` / `forms/ready_for_rehab.py:254–285`
**Impact:** Same six fields, same labels, same clean logic. Changes must be made in two files.

**Fix:** `R4RAcknowledgmentsForm` should inherit from `FHAcknowledgmentsForm`, or both inherit from a shared `BaseAcknowledgmentsForm`.

---

### 4.4 Renovation narrative form duplicated across FH and R4R (~60 lines)

**File:** `forms/featured_homes.py:76–125` / `forms/ready_for_rehab.py:204–251`
**Impact:** Same six fields (`intended_use`, `first_home_or_moving`, `renovation_description`, `renovation_who`, `renovation_when`, `renovation_funding`) and same `clean()` logic. Only placeholder text differs slightly.

**Fix:** Extract to `BaseRenovationNarrativeForm` with override points for placeholders.

---

### 4.5 Document context building duplicated three times in accordion.py

**File:** `accordion.py:1074–1087`, `1182–1195`, `1002–1017`
**Impact:** The block that builds required_docs, optional_docs, uploaded, required_count, etc. appears three times with identical logic.

**Fix:** Extract to `_build_document_context(program_type, purchase_type, form_data)`.

---

### 4.6 Renovation narrative template markup duplicated across FH and R4R

**File:** `templates/apply/v2/sections/fh/renovation_expanded.html:46–105` / `r4r/renovation_expanded.html:46–105`
**Impact:** ~60 lines of identical HTML (four textarea fields with Alpine char counters). Only the HTMX target ID differs.

**Fix:** Extract to `_renovation_narrative.html` partial with a `target_suffix` variable.

---

### 4.7 Ack section outer structure duplicated across three programs

**File:** `fh/acks_expanded.html`, `r4r/acks_expanded.html`, `vip/acks_expanded.html`
**Impact:** Section header, intro text, ack card loop, and submit button are identical. Only the closing info callout differs. ~45 lines × 3.

**Fix:** Extract shared structure to `_acks_base.html` with a `{% block closing_info %}` for program-specific content.

---

### 4.8 `_render_transition` is 130 lines assembling HTML via f-strings

**File:** `accordion.py:1127–1255`
**Impact:** Renders collapsed current section + expanded next section + OOB progress bar + OOB outline, all assembled with string concatenation. Fragile and hard to read.

**Fix:** Extract each render step into its own function, or use a dedicated partial template for the composite HTMX response.

---

### 4.9 Dead templates that should be removed

| File | Reason |
|------|--------|
| `templates/cotton/test_card.html` | Marked "delete after verifying cotton works" |
| `templates/cotton/nav_buttons.html` | Uses `type="submit"` incompatible with accordion; unused |
| `templates/cotton/doc_upload.html` | Replaced by `_document_capture.html`; unused |
| `templates/cotton/form_field.html` | Replaced by `c-field`; unused |
| `templates/apply/partials/renovation_totals.html` | Prior HTMX approach, replaced by client-side JS |
| `templates/apply/v2/_continue_button.html` | Legacy, replaced by `cotton/continue_btn.html` |

---

### 4.10 `submitted_at` uses `auto_now_add` — cannot be set explicitly

**File:** `applications/models.py:558`
**Impact:** `auto_now_add=True` makes the field non-writable. `created_at` and `submitted_at` are always identical. If you ever need to import historical data or recreate a record, you cannot set this field.

**Fix:** Use `null=True, blank=True` with no `auto_now_add`. Set explicitly in `submit_application()` with `timezone.now()`.

---

## 5. Performance

### 5.1 `DocsStateFilter` loads entire queryset into Python memory

**File:** `applications/admin.py:226–237`
**Impact:** When staff clicks the "Docs Complete" filter, all applications plus all their documents are loaded into RAM, evaluated in Python, then filtered by PK list. At 500+ applications with 3-5 docs each, this is 2,000+ rows into memory per filter click.

**Mitigation:** Acceptable at current scale (<100 apps). Document as known scaling limit. For >500 apps, replace with a `docs_complete` denormalized BooleanField updated on document save.

---

### 5.2 `get_dashboard_stats` makes 12 separate DB queries

**File:** `applications/admin_utils.py:20–122`
**Impact:** Status counts, unassigned, stale, my-review, recent, program counts, property counts — each is a separate query. Dashboard loads make 12 round-trips.

**Fix:** Consolidate into 3-4 queries using `Case/When` aggregates:
```python
stats = Application.objects.aggregate(
    total=Count("id"),
    received=Count("id", filter=Q(status="received")),
    under_review=Count("id", filter=Q(status="under_review")),
    # ...
)
```

---

### 5.3 Missing indexes on ApplicationDraft

**File:** `applications/models.py:177`
**Impact:** No index on `expires_at` (future cleanup queries will full-scan) or `(email, submitted)` (resume-by-email lookups).

**Fix:** Add to `ApplicationDraft.Meta`:
```python
indexes = [
    models.Index(fields=["expires_at"], name="idx_draft_expires"),
    models.Index(fields=["email", "submitted"], name="idx_draft_email_sub"),
]
```

---

### 5.4 `Application.docs_complete` relies on Django private internals

**File:** `applications/models.py:666–688`
**Impact:** The `_prefetched_objects_cache` check is a private API that could break on Django upgrades. Any code path without `prefetch_related("documents")` fires an additional query per application.

**Mitigation:** Short-term: document the prefetch requirement. Long-term: add a `docs_complete` denormalized field updated via signal on Document save.

---

### 5.5 `PropertyAdmin.application_count` double-annotates

**File:** `applications/admin.py:107–114, 75–80`
**Impact:** `get_queryset` annotates `_application_count` (underscore). `SBAdminField` also annotates `Count("applications")` (no underscore). Two identical annotations per query.

**Fix:** Remove one. Use the SBAdminField annotation and update the display method to read `instance.applications__count` or consolidate to a single annotation name.

---

## 6. Accessibility (WCAG Gaps)

### 6.1 `maximum-scale=1` blocks user zoom (WCAG 1.4.4 failure)

**File:** `templates/base.html:6`
**Impact:** Prevents all pinch-to-zoom. Low-vision users cannot magnify the form. The stated reason is preventing iOS auto-zoom on input focus.

**Fix:** Remove `maximum-scale=1`. Set `font-size: 16px` on all inputs (which prevents iOS auto-zoom without blocking user zoom).

---

### 6.2 Progress bar has no ARIA semantics

**File:** `templates/apply/v2/_progress_bar.html:15–19`
**Impact:** No `role="progressbar"`, no `aria-valuenow/min/max`. HTMX OOB updates are unannounced to screen readers.

**Fix:** Add `role="progressbar" aria-valuenow="{{ completed_count }}" aria-valuemin="0" aria-valuemax="{{ total_count }}" aria-label="Application progress"` to the progress track div. Add `aria-live="polite"` to the "Step X of Y" text.

---

### 6.3 Radio groups lack `fieldset`/`legend` grouping

**File:** `templates/cotton/radio_group.html:28–43`
**Impact:** Screen readers announce each radio input without the question text. Affects eligibility section, R4R prior purchase, VIP Q2/Q5, and all yes/no questions.

**Fix:** Replace `<div>/<p>` container with `<fieldset>/<legend>`.

---

### 6.4 All "Edit" buttons are ambiguously labeled

**File:** `templates/apply/v2/_summary_bar.html:22` (and 6 other collapsed templates)
**Impact:** A screen reader listing interactive elements announces six identical "Edit" buttons with no section context.

**Fix:** Add `<span class="sr-only">{{ section_title }}</span>` inside each Edit button.

---

### 6.5 Property search autocomplete is not keyboard navigable

**File:** `templates/apply/v2/sections/property_search_expanded.html` / `templates/apply/partials/property_results.html`
**Impact:** No `role="combobox"`, `aria-expanded`, or `aria-controls` on the search input. No `role="listbox"` or `role="option"` on results. Keyboard users cannot navigate with arrow keys.

**Fix:** Add ARIA combobox pattern: `role="combobox" aria-expanded="false" aria-controls="property-results"` on input. `role="listbox"` on results container. `role="option"` on each result button. Update `aria-expanded` via HTMX `afterSwap`.

---

### 6.6 Acknowledgment checkboxes have no explicit `id` attribute

**File:** `fh/acks_expanded.html:29`, `r4r/acks_expanded.html:29`, `vip/acks_expanded.html:29`
**Impact:** Implicit label association (wrapping `<label>` around `<input>`) technically works, but some screen readers in browse mode require explicit `for`/`id` linking.

**Fix:** Add `id="{{ field.html_name }}"` to each checkbox, `for="{{ field.html_name }}"` to its label.

---

### 6.7 `c-alert` dismiss button is only ~24px touch target

**File:** `templates/cotton/alert.html:55–59`
**Impact:** `p-1` yields ~24px. Project standard is 44px minimum per CLAUDE.md.

**Fix:** Change to `p-2.5` or add `min-w-[44px] min-h-[44px]` classes.

---

### 6.8 Application outline `<nav>` has no `aria-label`

**File:** `templates/apply/v2/_application_outline.html:7`
**Impact:** Multiple `<nav>` landmarks on a page are indistinguishable without labels.

**Fix:** `<nav aria-label="Application sections" class="space-y-1">`.

---

### 6.9 Entity dropdown chevron SVG not hidden from screen readers

**File:** `templates/apply/v2/_entity_dropdown.html:11`
**Impact:** Decorative SVG announced as meaningless content.

**Fix:** Add `aria-hidden="true"` to the SVG element.

---

## 7. Testing Gaps

### Current state: 7 tests in 1 file

`applications/tests.py` has 3 test classes with 7 methods. No CI step runs them.

### Critical paths with zero test coverage:

| Area | Risk Level | Recommended Tests |
|------|-----------|-------------------|
| **Submission end-to-end** (all 3 programs) | Critical | `test_fh_cash_submission_creates_application_and_documents`, `test_r4r_submission_stores_line_item_totals`, `test_vip_submission_stores_proposal_fields` |
| **Down payment validation** (two thresholds) | Critical | `test_below_10_percent_rejected`, `test_below_1000_floor_rejected`, `test_at_10_percent_accepted`, `test_required_for_land_contract` |
| **Eligibility gate** (hard block) | High | `test_delinquent_taxes_blocks`, `test_foreclosure_blocks`, `test_both_no_advances` |
| **Draft expiration + resume** | High | `test_is_expired_property`, `test_get_draft_creates_new_when_expired`, `test_resume_expired_shows_link_expired`, `test_resume_submitted_shows_already_submitted` |
| **Document upload validation** | High | `test_pdf_wrong_magic_bytes_rejected`, `test_disallowed_extension_rejected`, `test_file_over_10mb_rejected`, `test_required_doc_missing_blocks_advance` |
| **Admin permissions** | Medium | `test_non_superuser_cannot_delete`, `test_has_add_permission_always_false` |
| **Reference number generation** | Medium | `test_first_app_gets_0001`, `test_sequential_numbering` |
| **HTMX partials** | Medium | `test_purchase_type_fields_shows_land_contract`, `test_renovation_totals_calculates_correctly`, `test_property_search_returns_results` |
| **Form clean methods** | Medium | `test_fh_renovation_requires_first_home_when_move_in`, `test_vip_q2_requires_detail_when_yes`, `test_r4r_line_items_calculate_totals` |

### CI gap

`.github/workflows/pylint.yml` runs only linting. Add a Django test step:
```yaml
- name: Run tests
  run: python manage.py test applications --verbosity=2
  env:
    DATABASE_URL: sqlite:///test.db
    SECRET_KEY: test-only-key
```

---

## Priority Matrix

| # | Item | Impact | Effort | Category |
|---|------|--------|--------|----------|
| 1.1 | `full_clean()` before save | Data integrity | 1 line | Critical |
| 1.2 | `open_house_date` crash | Buyer-facing crash | Small | Critical |
| 1.3 | Wrong summary key for R4R | Display bug | 1 line | Critical |
| 1.4 | Double-submit race condition | Duplicate records | Small | Critical |
| 1.5 | Path traversal in `_move_documents` | Security | Small | Critical |
| 1.6 | No state transition enforcement | Workflow integrity | Medium | Critical |
| 6.1 | `maximum-scale=1` blocks zoom | WCAG failure | 1 line | Critical |
| 2.1 | Error clearing too aggressive | Buyer confusion | Small | High |
| 2.7 | Non-field errors swallowed | Buyer confusion | Small | High |
| 3.1 | Blank dashboard | Staff productivity | Medium | High |
| 6.2 | Progress bar no ARIA | Screen reader UX | Small | High |
| 6.3 | Radio groups no fieldset | Screen reader UX | Medium | High |
| 6.5 | Autocomplete not keyboard navigable | Keyboard UX | Medium | High |
| 7.x | Add submission e2e tests | Regression safety | Large | High |
| 7.x | Add CI test step | Automated safety | Small | High |
| 1.8 | VIP NullBooleanField | Data validation | Small | Medium |
| 1.9 | No section ordering check | Security | Small | Medium |
| 1.10 | Rate limiting gaps | Abuse prevention | Small | Medium |
| 2.6 | HTMX race conditions | UX glitch | Small | Medium |
| 3.2 | Bulk actions bypass validation | Workflow | Medium | Medium |
| 4.1 | Split accordion.py | Maintainability | Medium | Medium |
| 4.3–4.7 | DRY refactors | Maintainability | Medium | Low |
| 4.9 | Remove dead templates | Hygiene | Small | Low |
| 5.1–5.5 | Performance optimizations | Scalability | Medium | Low |

---

## Execution Order Recommendation

**Phase A — Before launch (Critical + High):**
1. Fix items 1.1–1.5 (one-liner to small fixes, data integrity)
2. Fix item 1.6 (state machine — medium effort, workflow integrity)
3. Fix item 6.1 (remove `maximum-scale=1`)
4. Fix items 2.1, 2.7 (error display)
5. Add submission e2e tests + CI test step
6. Fix ARIA gaps (6.2, 6.3, 6.4)

**Phase B — Post-launch polish:**
1. Wire up SmartBase dashboard (3.1)
2. HTMX sync attributes (2.6)
3. Bulk action validation (3.2)
4. DRY refactors (4.3–4.7)
5. Dead template cleanup (4.9)

**Phase C — Scale prep:**
1. Split accordion.py (4.1)
2. Performance optimizations (5.1–5.5)
3. Full WCAG audit for remaining gaps (6.5–6.9)
4. Comprehensive test suite buildout
