# Implementation Plan: Tailwind Build Pipeline + Cotton Components

**Date:** 2026-02-28
**Branch:** `feature/tailwind-build-cotton` (or current `feature/smartbase-admin-swap`)
**Spec:** `TASK-tailwind-build-and-cotton-components.md`
**Goal:** Replace Tailwind Play CDN with compiled CSS; introduce cotton components for form field DRY-up. **Zero visual changes.**

---

## Infrastructure Audit: What Already Exists

The spec assumes greenfield. In reality, significant infrastructure is already in place:

| Spec Step | Status | What Exists |
|-----------|--------|-------------|
| 1.1 Install Tailwind | **DONE** | `theme/static_src/node_modules/` has tailwindcss 3.4.17, @tailwindcss/forms, postcss, autoprefixer |
| 1.2 Create tailwind.config.js | **DONE** | `theme/static_src/tailwind.config.js` — full color tokens, fonts, animations, content paths |
| 1.3 Create source CSS | **PARTIAL** | `theme/static_src/src/styles.css` exists but only has 3 `@tailwind` directives — no custom CSS migrated |
| 1.4 Build scripts | **DONE** | `theme/static_src/package.json` has `build` and `dev` scripts |
| 1.5 Initial build | **DONE** | `theme/static/css/dist/styles.css` exists (55KB compiled, Tailwind utilities only) |
| 1.6 Update base.html | **NOT DONE** | CDN script + inline config + ~580 lines of `<style>` still in base.html |
| 1.7 .gitignore | **PARTIAL** | Need to verify node_modules/ and dist/ are ignored |
| 1.9 Procfile | **NOT DONE** | No CSS build step before collectstatic |
| 2.1 Install django-cotton | **DONE** | `django_cotton.apps.SimpleAppConfig` in INSTALLED_APPS, loaders + builtins configured |
| 2.2 Cotton directory | **DONE** | `templates/cotton/` has 9 existing components |
| 2.12 requirements.txt | **DONE** | `django-cotton>=1.0.0` and `django-tailwind>=3.8.0` already listed |

### Key Differences from Spec

1. **File paths differ:** Spec uses `static/css/src/main.css` → `static/css/dist/main.css`. Existing infrastructure uses `theme/static_src/src/styles.css` → `theme/static/css/dist/styles.css`. **Use existing paths** — django-tailwind manages the theme app convention.

2. **@tailwindcss/forms strategy:** Existing config loads the plugin WITHOUT `strategy: 'class'`. The spec says this is critical. Need to add `{ strategy: 'class' }` so the forms plugin doesn't globally override our `.gclba-input` styles.

3. **Extra plugins:** Existing config has `@tailwindcss/typography` and `@tailwindcss/aspect-ratio` beyond what spec requires. Keep them — they don't hurt and may be useful.

4. **PostCSS extras:** Existing postcss.config.js has `postcss-import`, `postcss-simple-vars`, `postcss-nested` beyond basic autoprefixer. These enable CSS nesting and variables in the source file — useful for the custom CSS migration.

5. **Build commands:** Use `python manage.py tailwind build` (django-tailwind wrapper) rather than standalone `npx tailwindcss`. This handles paths automatically.

6. **Existing cotton `form_field.html`:** Uses slot pattern (wraps `{{ slot }}`). Spec proposes self-closing `<c-field>` that embeds the `<input>` internally. Create the NEW components alongside the existing ones — don't break the 9 existing components.

7. **`_field_label.html` is unused:** Grep confirms zero references. Safe to delete.

---

## Phase 1: Activate the Tailwind Build Pipeline

The infrastructure is already installed. We need to: migrate custom CSS into the source file, add `strategy: 'class'` to the forms plugin, rebuild, swap base.html from CDN to compiled stylesheet, and update the deploy pipeline.

### Task 1.1: Add `strategy: 'class'` to @tailwindcss/forms plugin

**File:** `theme/static_src/tailwind.config.js`

Change:
```js
plugins: [
  require("@tailwindcss/forms"),
```
To:
```js
plugins: [
  require("@tailwindcss/forms")({ strategy: "class" }),
```

**Why:** Without `strategy: 'class'`, the forms plugin applies global resets to ALL form elements. This would override our existing `.gclba-input` and `.gclba-select` styles, causing visual regressions. With `strategy: 'class'`, the plugin only activates when you explicitly add its utility classes (like `form-input`, `form-select`). Since we don't use those classes, this effectively makes the plugin a no-op that's available if needed later.

**Verification:** Run `python manage.py tailwind build` — should compile without errors.

---

### Task 1.2: Migrate custom CSS from base.html into source file

**Source:** `templates/base.html` lines ~40-620 (the entire `<style>` block)
**Target:** `theme/static_src/src/styles.css` (append after the 3 `@tailwind` directives)

Move ALL custom CSS rules from the `<style>` block in base.html into the source CSS file. This includes:

1. **Form inputs:** `.gclba-input`, `.gclba-select`, focus states, has-error states
2. **Buttons:** `.gclba-btn-primary`, `.continue-btn`, `.doc-capture-btn-primary`
3. **Section structure:** `.section-card-v2`, `.section-body`, `.section-body.expanded`
4. **Summary bars:** `.summary-bar`, hover states, edit buttons
5. **Progress:** `.progress-strip`, `.progress-pill`, `.progress-pill-track`, `.progress-pill-fill`, `.progress-pill-label`
6. **Touch targets:** `.touch-label`, radio checked states via `:has()`, disabled states
7. **Accordion:** `.accordion-section`, `.accordion-gap`, `.accordion-gap-active`
8. **Dividers:** `.field-divider`, `.section-divider`
9. **Animations:** `@keyframes fadeSlideIn`, `stepIn`, `scaleIn`, etc.
10. **Focus behavior:** `.space-y-1\.5:focus-within > label:first-child` color shift
11. **Entity dropdown:** `.entity-dropdown` styles
12. **Ack cards:** checkbox `:has(:checked)` green state
13. **Document upload:** `.doc-capture-btn`, upload zone styling
14. **Reduced motion:** `@media (prefers-reduced-motion: reduce)`
15. **Mobile:** `@media` breakpoint overrides, touch target sizing
16. **Civic background:** `.civic-bg` gradient
17. **Everything else** — if it's in the `<style>` block, it goes in the CSS file

**Do NOT move:**
- Google Fonts `<link>` tags (stay in `<head>`)
- HTMX `<script>` tag (stays in base.html)
- Any inline `<script>` blocks for JS behavior

**PostCSS advantage:** The existing postcss.config.js has `postcss-nested`, so you CAN use CSS nesting syntax if it makes the migration cleaner. But preserving the existing flat structure is fine too — just copy-paste.

**Verification:**
- `python manage.py tailwind build` succeeds
- Output `theme/static/css/dist/styles.css` grows significantly (should be much larger than the current 55KB)

---

### Task 1.3: Update base.html — swap CDN for compiled CSS

**File:** `templates/base.html`

**Remove these three elements from `<head>`:**
1. `<script src="https://cdn.tailwindcss.com"></script>` (the CDN script)
2. The entire `<script>tailwind.config = { ... }</script>` block (inline config)
3. The entire `<style> ... </style>` block (custom CSS — now in the source file)

**Add in their place:**
```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/dist/styles.css' %}">
```

**Keep unchanged:**
- Google Fonts `<link>` tags
- HTMX `<script src="..."></script>` tag
- Any JS `<script>` blocks (event delegation, error clearing, etc.)
- `<meta>` tags (viewport, charset, etc.)
- Header, footer, main content area

**Static file path note:** The compiled CSS lives at `theme/static/css/dist/styles.css`. After `collectstatic`, WhiteNoise serves it from `STATIC_ROOT/css/dist/styles.css`. The `{% static %}` tag resolves this automatically. The `theme/` prefix is NOT needed in the template tag because Django's `AppDirectoriesFinder` maps `theme/static/` as a static files root.

**Critical:** `CompressedManifestStaticFilesStorage` will crash with `ValueError` if the file reference doesn't exist in the manifest. Run `collectstatic` after building CSS but BEFORE testing the dev server. Or temporarily switch to `WhiteNoiseMiddleware` with `WHITENOISE_USE_FINDERS = True` for development.

**Dev workflow consideration:** For local development with `DEBUG=True`, Django's `staticfiles` app serves files directly from source dirs using finders. The compiled CSS at `theme/static/css/dist/styles.css` will be found by `AppDirectoriesFinder`. No `collectstatic` needed for dev — just `python manage.py tailwind build` (or `tailwind start` for watch mode).

---

### Task 1.4: Update .gitignore

**File:** `.gitignore`

Ensure these are present:
```
# Tailwind / Node
theme/static_src/node_modules/
theme/static/css/dist/

# Django
staticfiles/
```

The compiled CSS is a build artifact — it should not be committed. Railway will build it on deploy.

---

### Task 1.5: Update Procfile for Railway deploy

**File:** `Procfile`

Current:
```
web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
```

New:
```
web: cd theme/static_src && npm install && npm run build && cd ../.. && python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
```

**OR** use `python manage.py tailwind build` if django-tailwind handles npm install internally:
```
web: python manage.py tailwind install && python manage.py tailwind build && python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
```

**Railway requirement:** Railway's Nixpacks builder detects both Python and Node.js when `package.json` is present. However, the `theme/static_src/package.json` is nested — Railway may not auto-detect it. The explicit `cd` + `npm install` + `npm run build` in the Procfile ensures it runs regardless.

**Alternative:** Use a `nixpacks.toml` or `railway.json` build phase. But per CLAUDE.md, Procfile is the source of truth. Keep it in Procfile.

**Verification:** Deploy to Railway, check that `/apply/` loads without unstyled flash. Check Railway build logs for the npm install + build step completing successfully.

---

### Task 1.6: Verify Phase 1 — pixel-identical output

**Local verification steps:**

1. `python manage.py tailwind build` — compiles CSS
2. `python manage.py runserver 8199` — start dev server
3. Open `http://localhost:8199/apply/` in browser

**Check:**
- [ ] No request to `cdn.tailwindcss.com` in Network tab
- [ ] Single CSS file served from `/static/css/dist/styles.css`
- [ ] All form fields styled correctly (blue focus ring, warm background)
- [ ] Continue buttons show program accent color
- [ ] Section cards have top border + number badge
- [ ] Collapsed summary bars display correctly
- [ ] Progress bar animates
- [ ] Radio buttons have 44px touch targets
- [ ] Dropdown chevrons appear on selects
- [ ] Mobile viewport: no iOS zoom on input focus, touch targets adequate
- [ ] Ack cards turn green on check
- [ ] HTMX interactions still fire (intended use swap, eligibility gate, etc.)
- [ ] No browser console errors

**Commit after Phase 1 passes.** This is a clean breakpoint — the Tailwind build works independently of the cotton component refactoring.

---

## Phase 2: Cotton Components for Form Fields

### Task 2.1: Create `<c-field>` — text input component

**File:** `templates/cotton/field.html` (NEW — alongside existing `form_field.html`)

Self-closing text input with label, required asterisk, hint, error, and all HTML attributes. See spec section 2.3 for full code.

**Props:** `name`, `label`, `value`, `type` (default "text"), `placeholder`, `required`, `hint`, `right_hint`, `error`, `inputmode`, `autocomplete`, `autocapitalize`, `css_class`, `id`, `mono`

**Key differences from existing `form_field.html`:**
- Self-closing: embeds the `<input>` tag internally (no `{{ slot }}`)
- More props: `inputmode`, `autocomplete`, `autocapitalize`, `mono`, `right_hint`
- Simpler to use in templates: one tag per field instead of component + inner input

**Coexistence:** Both `<c-field>` and `<c-form_field>` will work. Existing uses of `<c-form_field>` are NOT broken by adding `<c-field>`. Migrate templates one at a time.

---

### Task 2.2: Create `<c-textarea>` — textarea component

**File:** `templates/cotton/textarea.html` (NEW)

See spec section 2.4 for full code.

**Props:** `name`, `label`, `value`, `placeholder`, `required`, `hint`, `error`, `rows` (default "3"), `id`, `css_class`

---

### Task 2.3: Create `<c-select>` — select dropdown component

**File:** `templates/cotton/select.html` (NEW)

Uses `{{ slot }}` for `<option>` elements — you still need to loop over choices in the template. This is correct because option values come from Django form fields and vary per field.

**Props:** `name`, `label`, `required`, `hint`, `error`, `id`, `css_class`, `hx_post`, `hx_target`, `hx_swap` (default "innerHTML"), `hx_include`

See spec section 2.5 for full code.

---

### Task 2.4: Create `<c-radio-group>` — radio button group

**File:** `templates/cotton/radio_group.html` (NEW — note: underscore, not hyphen, for cotton file naming)

Uses `{{ slot }}` for the radio button labels (these contain HTMX and conditional logic that varies).

**Props:** `label`, `required`, `error`, `layout` (default "row")

See spec section 2.6 for full code.

**Note on cotton file naming:** Django-cotton converts component names from `<c-radio-group>` to file lookup `radio-group.html` or `radio_group.html`. Use underscore (`radio_group.html`) to match Python conventions and avoid potential path issues.

---

### Task 2.5: Create `<c-section-header>` — expandable section wrapper

**File:** `templates/cotton/section_header.html` (NEW)

Wraps the section card with top border, number badge, title, subtitle, and the expanded body area. Uses `{{ slot }}` for the section's field content.

**Props:** `number`, `title`, `subtitle`, `color` (default "#2E7D32")

See spec section 2.7 for full code.

---

### Task 2.6: Create `<c-continue-btn>` — section continue button

**File:** `templates/cotton/continue_btn.html` (NEW)

Standardized HTMX continue button with program color and chevron icon.

**Props:** `validate_url`, `section_id`, `program_color` (default "#2E7D32"), `label` (default "Continue")

See spec section 2.8 for full code.

---

### Task 2.7: Refactor `contact_expanded.html` — proof of concept

**File:** `templates/apply/v2/sections/contact_expanded.html`

This is the best POC candidate — lots of simple text inputs, one email, one phone, one select. No HTMX complexity.

**Refactoring rules:**
1. Replace the outer section card markup with `<c-section-header>`
2. Replace each text `<div class="space-y-1.5">` + label + input + error block with `<c-field>`
3. Replace the email field with `<c-field type="email">`
4. Replace the phone field with `<c-field type="tel" inputmode="tel">`
5. Replace the preferred contact select with `<c-select>`
6. Replace the continue button with `<c-continue-btn>`
7. Keep the entity dropdown as-is (too custom for a generic component)
8. Keep all `name`, `id`, and `value` attributes IDENTICAL — form validation depends on these

**Before/After example (first name field):**

Before (~8 lines):
```html
<div class="space-y-1.5">
    <label for="{{ form.first_name.id_for_label }}" class="block text-sm font-medium text-warm-900">
        First Name <span class="text-red-500 text-xs">*</span>
    </label>
    <input type="text" name="{{ form.first_name.html_name }}" id="{{ form.first_name.id_for_label }}"
           value="{{ form.first_name.value|default:'' }}" required
           placeholder="First name" class="gclba-input{% if form.first_name.errors %} has-error{% endif %}">
    {% if form.first_name.errors %}<p class="text-xs text-red-600 font-medium">{{ form.first_name.errors.0 }}</p>{% endif %}
</div>
```

After (~9 lines but zero boilerplate):
```html
<c-field
  name="{{ form.first_name.html_name }}"
  id="{{ form.first_name.id_for_label }}"
  label="First Name"
  value="{{ form.first_name.value|default:'' }}"
  placeholder="First name"
  required="true"
  autocomplete="given-name"
  autocapitalize="words"
  error="{{ form.first_name.errors.0 }}"
/>
```

**Verification:** Open `/apply/`, fill in Step 1 (Contact), verify all fields render identically, validation errors still appear, HTMX continue button still works.

---

### Task 2.8: Refactor shared section templates

Work through these templates, applying cotton components where they fit:

1. **`property_expanded.html`** — text inputs + property search (keep the HTMX search as-is, use `<c-field>` for simple fields, `<c-select>` for program type)
2. **`property_search_expanded.html`** — if this exists as a separate expanded template, refactor similarly
3. **`eligibility_expanded.html`** — uses `<c-radio-group>` for the two Yes/No questions. Already uses `<c-alert>` for the disqualification message — keep that.
4. **`program_expanded.html`** — likely just program cards, may not have form fields to componentize

**Rules:**
- Don't force components onto complex custom markup
- If a field has HTMX attributes (`hx-post`, `hx-target`), use `<c-select>` with the `hx_*` props
- Dollar amounts: `<c-field inputmode="decimal" mono="true">`
- Keep all field names and IDs identical

---

### Task 2.9: Refactor Featured Homes section templates

1. **`fh/offer_expanded.html`** — offer amount (money field), purchase type select (HTMX), down payment (conditional), self-employed toggle
2. **`fh/documents_expanded.html`** — skip file upload zones (too custom), use components for any text fields
3. **`fh/renovation_expanded.html`** — intended use select (HTMX), textareas for renovation narrative, `<c-continue-btn>`
4. **`fh/acks_expanded.html`** — acknowledgment checkboxes (ack cards use `:has(:checked)` CSS — keep as-is or create a component if pattern is consistent)
5. **`homebuyer_ed_expanded.html`** — homebuyer education fields

---

### Task 2.10: Refactor R4R section templates

1. **`r4r/offer_expanded.html`** — simpler than FH (cash only, no purchase type choice)
2. **`r4r/documents_expanded.html`** — skip file upload zones
3. **`r4r/line_items_expanded.html`** — money fields with `inputmode="decimal"` and `font-mono`. Each line item is a `<c-field>` with `mono="true"`. Keep the HTMX auto-calculation JavaScript as-is.
4. **`r4r/renovation_expanded.html`** — intended use select (HTMX), textareas, continue button
5. **`r4r/acks_expanded.html`** — acknowledgment checkboxes

---

### Task 2.11: Refactor VIP section templates

1. **`vip/proposal_expanded.html`** — 8 proposal question textareas — great candidate for `<c-textarea>` x8
2. **`vip/documents_expanded.html`** — skip file upload zones
3. **`vip/acks_expanded.html`** — VIP-specific acknowledgments

---

### Task 2.12: Delete unused proto-component

**File:** `templates/apply/v2/_field_label.html` — DELETE

Grep confirms zero references across all templates. This was a proto-component that was never fully adopted. The cotton components replace it.

---

### Task 2.13: Verify Phase 2 — full regression check

**Automated:**
```bash
python manage.py check
python manage.py tailwind build
python manage.py test applications
```

**Manual — walk through all 3 programs:**

Featured Homes (Cash):
- [ ] Contact section: all fields render, validate, errors show
- [ ] Property section: search works, program select works
- [ ] Eligibility: radio buttons work, disqualification gate works
- [ ] Offer: amount field, no purchase type for cash
- [ ] Documents: upload zones work
- [ ] Renovation: intended use HTMX swap, textarea fields
- [ ] Acks: checkbox cards turn green
- [ ] Submit: creates Application record

Featured Homes (Land Contract):
- [ ] Offer: purchase type select, down payment appears, validation
- [ ] Documents: land contract docs appear
- [ ] Homebuyer Ed: fields render

Ready for Rehab:
- [ ] Offer: cash only (no purchase type shown)
- [ ] Documents: R4R-specific docs, prior purchase conditional
- [ ] Line Items: all money fields, auto-calculation, subtotals
- [ ] Renovation: same as FH

VIP Spotlight:
- [ ] Proposal: 8 textarea questions render
- [ ] Documents: VIP docs + portfolio upload
- [ ] Acks: VIP-specific acknowledgments

Cross-cutting:
- [ ] Save and resume (magic link) still works
- [ ] Mobile viewport: touch targets, no iOS zoom
- [ ] No browser console errors
- [ ] CSS served from compiled file, no CDN request

---

## Phase 3: Performance & Deploy Verification

### Task 3.1: Performance comparison

Open Chrome DevTools Network tab on `/apply/`:

**Before (CDN):**
- `cdn.tailwindcss.com` script: ~XXX KB + runtime JIT compilation on every page load
- Inline `<style>` block: rendered in HTML on every request

**After (compiled):**
- Single CSS file: should be well under 50KB minified + gzipped
- No runtime compilation
- Cached by browser after first load (WhiteNoise adds cache headers)
- No layout shift during page load

### Task 3.2: Deploy to Railway

1. Push branch to GitHub
2. Railway builds: npm install + npm build + collectstatic + migrate
3. Verify `/apply/` on Railway URL loads correctly
4. Check Railway build logs for CSS compilation step
5. Verify no CDN requests in production

---

## Execution Order & Commit Strategy

| Batch | Tasks | Commit Message |
|-------|-------|----------------|
| 1 | 1.1, 1.2, 1.3, 1.4 | `feat(css): migrate Tailwind from CDN to compiled build pipeline` |
| 2 | 1.5, 1.6 | `chore(deploy): add CSS build step to Procfile and .gitignore` |
| 3 | 2.1–2.6 | `feat(cotton): add field/textarea/select/radio/section/continue components` |
| 4 | 2.7 | `refactor(apply): convert contact section to cotton components` |
| 5 | 2.8 | `refactor(apply): convert shared sections to cotton components` |
| 6 | 2.9 | `refactor(apply): convert Featured Homes sections to cotton components` |
| 7 | 2.10 | `refactor(apply): convert R4R sections to cotton components` |
| 8 | 2.11 | `refactor(apply): convert VIP sections to cotton components` |
| 9 | 2.12, 2.13 | `chore(apply): delete unused _field_label proto-component` |

**Review checkpoints:** After Batch 1 (Phase 1 complete — verify visuals), after Batch 4 (POC template — verify component approach works), after Batch 8 (all templates — full regression).

---

## Rollback Plan

Phase 1 and Phase 2 are independently reversible:

**Revert Phase 1 (Tailwind build):**
1. Restore `templates/base.html` from git (restores CDN + inline config + inline styles)
2. Revert Procfile
3. No model/migration changes

**Revert Phase 2 (Cotton components):**
1. Restore section templates from git
2. Delete new `templates/cotton/field.html`, `textarea.html`, `select.html`, `radio_group.html`, `section_header.html`, `continue_btn.html`
3. No model/migration changes, no settings changes needed (cotton was already installed)

Both phases are purely template-level. No database changes, no Python logic changes, no data affected.

---

## Files Summary

| File | Action | Phase |
|------|--------|-------|
| `theme/static_src/tailwind.config.js` | EDIT (add strategy: 'class') | 1 |
| `theme/static_src/src/styles.css` | EDIT (append ~580 lines of custom CSS) | 1 |
| `templates/base.html` | EDIT (remove CDN + inline config + style block, add stylesheet link) | 1 |
| `.gitignore` | EDIT (add node_modules/ and dist/) | 1 |
| `Procfile` | EDIT (add CSS build step before collectstatic) | 1 |
| `templates/cotton/field.html` | NEW | 2 |
| `templates/cotton/textarea.html` | NEW | 2 |
| `templates/cotton/select.html` | NEW | 2 |
| `templates/cotton/radio_group.html` | NEW | 2 |
| `templates/cotton/section_header.html` | NEW | 2 |
| `templates/cotton/continue_btn.html` | NEW | 2 |
| `templates/apply/v2/sections/*.html` (18 files) | EDIT (refactor to use components) | 2 |
| `templates/apply/v2/_field_label.html` | DELETE | 2 |
| `config/settings.py` | NO CHANGE (already configured) | — |
| `requirements.txt` | NO CHANGE (deps already listed) | — |
