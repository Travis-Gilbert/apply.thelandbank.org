# Design: Beauty, Mobile Craft & Visual Polish Upgrade

**Date:** 2026-02-20
**Status:** Approved
**Scope:** CSS/JS/template changes across buyer-facing templates — no model or view changes

---

## Goals

1. **Typography & hierarchy** — create clear visual chapters, not a uniform stream
2. **Visual polish & delight** — break the sameness, add memorable moments
3. **Mobile craft** — make the phone experience feel intentional and native

---

## Priority Order (implementation batches)

### Batch 1: Typography Foundation
Highest impact, lowest risk. Changes the feel of every page.

### Batch 2: Mobile Craft
Second-highest impact — most users are on phones.

### Batch 3: Visual Polish & Delight
The memorable moments. Builds on the foundation from Batches 1-2.

---

## Batch 1: Typography & Information Hierarchy

### 1A. Step titles — bigger and bolder
**Files:** `base_form.html`
- Step title: `text-xl sm:text-2xl` → `text-2xl sm:text-3xl` with `leading-tight`
- Add a short program-colored dash/accent under the title (4px wide, 40px long, rounded)
- Step number circle: current `w-8 h-8` → `w-9 h-9` with `text-sm font-bold`
- Subtitle text: `text-sm` → `text-[15px]` with slightly more `leading-relaxed`

### 1B. Section labels — more breathing room
**Files:** `_section_label.html`, `base.html` (CSS)
- Background: add subtle gradient from `rgba(250, 248, 244, 0.6)` to `transparent`
- Bottom margin: `mb-5` → `mb-6`
- Icon badge: `w-7 h-7` → `w-8 h-8`, icon size `text-xs` → `text-sm`
- Add `padding-bottom: 0.875rem` for more vertical breathing room

### 1C. Field labels — required vs optional visual rhythm
**Files:** `_field.html`
- Required fields: labels remain `font-medium text-warm-900` (current)
- Optional fields: labels become `font-normal text-warm-600` with `(optional)` suffix in `text-warm-400 text-xs`
- Pass `optional=True` to `_field.html` include for non-required fields
- Effect: creates bold/light scanning rhythm across the form

### 1D. Dollar amounts and totals — proud numbers
**Files:** `r4r/step_line_items.html`, `partials/renovation_totals.html`
- Subtotal rows: `text-base font-mono` → `text-lg font-mono font-bold`
- Grand total: `text-lg` → `text-xl font-mono font-extrabold`
- Grand total row: distinct background — `bg-civic-green-50 border-t-2 border-civic-green-600` with `py-4 px-5 rounded-b-xl`
- Offer amount display (confirmation page): `text-lg font-mono` → `text-xl font-mono font-bold`

### 1E. Confirmation page — typographic celebration
**Files:** `confirmation.html`
- Reference number: `text-lg font-mono font-bold` → `text-3xl font-mono font-bold tracking-wider`
- Reference number container: "ticket stub" treatment — horizontal card with dashed right border, warm paper background `bg-warm-50`, left program-color accent border 4px
- "What happens next" list: convert from `<ol>` to visual timeline — numbered circles (program-colored) connected by vertical line, with text beside each node
- Section heading "Your Application Summary": `text-lg` → `text-xl`

### 1F. Optional section card visual differentiation
**Files:** `step_identity.html` (Purchasing Entity card), `base.html` (CSS)
- New CSS class `.section-card-optional`: dashed border instead of solid, slightly more transparent background (`rgba(255,255,255,0.6)`), border color `rgba(210, 204, 194, 0.35)`
- Apply to "Purchasing Entity" section and any other explicitly optional sections
- Visually communicates "you can skip this" before reading the text

---

## Batch 2: Mobile Craft

### 2A. Fixed bottom navigation bar
**Files:** `base_form.html`, `base.html` (CSS)
- On mobile (`max-width: 639px`), the navigation bar becomes `position: fixed; bottom: 0; left: 0; right: 0`
- Frosted glass treatment: `backdrop-filter: blur(12px); background: rgba(255,255,255,0.9)`
- Continue button: full-width, 52px height, `text-base font-semibold`
- Back + Save buttons: secondary row above Continue, smaller
- `padding-bottom` added to form content area to prevent overlap with fixed bar
- Slides up with `translateY(100%) → translateY(0)` on page load (300ms ease)
- On final step (submit): gold top border `3px solid #d4a843` matching header accent
- Desktop: unchanged (stays inline at bottom of form)

### 2B. Field focus label color shift
**Files:** `base.html` (CSS)
- When field gets focus, its parent `label` transitions color to `civic-green-700`
- CSS approach: `.space-y-1\\.5:focus-within > label:first-child { color: #256929; transition: color 0.15s; }`
- Hint text below focused field: opacity increases from default `0.85` to `1`
- Subtle but creates sense of form "responding" to your touch

### 2C. Progress bar spark animation
**Files:** `base.html` (CSS), `base_form.html` (JS)
- After progress bar fill animates to new width, a `::after` pseudo-element slides across the filled portion — a white gradient that moves left→right over 400ms then fades
- CSS keyframe `@keyframes progressSpark` on `.progress-pill-fill::after`
- Triggered by adding `.just-advanced` class on page load, removed after animation completes
- Step number in pill badge: `@keyframes stepBounce { 0% { transform: scale(1) } 50% { transform: scale(1.15) } 100% { transform: scale(1) } }` — 300ms, runs once

### 2D. Scroll-aware card reveal
**Files:** `base.html` (CSS + JS)
- New CSS: `.reveal-on-scroll { opacity: 0; transform: translateY(12px); transition: opacity 0.4s ease, transform 0.4s ease; }`
- `.reveal-on-scroll.is-visible { opacity: 1; transform: translateY(0); }`
- JS: `IntersectionObserver` with `threshold: 0.1` adds `.is-visible` when card enters viewport
- Only applies to cards below the fold (check `getBoundingClientRect().top > window.innerHeight` on load)
- Cards visible on load get `.is-visible` immediately (no animation)
- Stagger: each successive card gets +60ms `transition-delay`

### 2E. Touch feedback `:active` states
**Files:** `base.html` (CSS)
- Radio pills / purchase type cards: `active { transform: scale(0.97); transition: transform 100ms; }`
- Continue/Submit button: `active { transform: scale(0.98); box-shadow: 0 1px 2px rgba(46,125,50,0.4); }`
- Ack checkboxes: `active { background-color: rgba(46,125,50,0.04); }`
- Summary bar Edit button: `active { background: rgba(0,0,0,0.06); }`
- All CSS-only, no JS required

### 2F. Smart autocomplete attributes
**Files:** `step_identity.html`, `_field.html`
- `first_name`: `autocomplete="given-name" autocapitalize="words"`
- `last_name`: `autocomplete="family-name" autocapitalize="words"`
- `email`: `autocomplete="email"`
- `phone`: `autocomplete="tel"`
- `mailing_address`: `autocomplete="street-address" autocapitalize="words"`
- `city`: `autocomplete="address-level2" autocapitalize="words"`
- `state`: `autocomplete="address-level1"`
- `zip_code`: `autocomplete="postal-code"`
- Add `autocomplete` parameter to `_field.html` include: `{% if autocomplete %}autocomplete="{{ autocomplete }}"{% endif %}`
- Add `autocapitalize` parameter similarly

### 2G. Offer amount blur formatting
**Files:** `fh/step_offer.html`, `r4r/step_offer.html` (inline JS or base.html)
- On `blur` event for offer amount: format display as `$12,500.00`
- On `focus` event: revert to raw number for editing
- Store raw value in a hidden input, display formatted value in visible input
- Or simpler: use `Intl.NumberFormat` on blur to set `value`, strip on focus
- Ensures the number the user typed is always what submits

---

## Batch 3: Visual Polish & Delight

### 3A. Confirmation page confetti
**Files:** `confirmation.html`, `base.html` (CSS)
- CSS-only confetti: 15-20 small `<div>` elements absolutely positioned, each with:
  - Random rotation via inline `style` (set in template)
  - `@keyframes confettiFall { from { opacity: 1; transform: translateY(-20px) rotate(0deg); } to { opacity: 0; transform: translateY(100vh) rotate(720deg); } }`
  - Duration: 2-3.5s each (varied via inline style)
  - `animation-fill-mode: forwards` — confetti disappears after falling
- Colors: program-specific (Featured Homes: greens/golds, R4R: oranges/ambers, VIP: blues/silvers)
- Generated with a Django template loop: `{% for i in "123456789012345" %}` with varied positions/sizes

### 3B. Confirmation success icon pulse ring
**Files:** `confirmation.html`, `base.html` (CSS)
- `@keyframes pulseRing { 0% { opacity: 0.6; transform: scale(1); } 100% { opacity: 0; transform: scale(1.6); } }`
- `::before` pseudo-element on the success icon container
- Repeats 2 times then stops (`animation-iteration-count: 2`)
- Ring color matches program color at 30% opacity

### 3C. Disqualified page — softer treatment
**Files:** `disqualified.html`
- Icon: red X → amber information circle (⚠ style, not ❌ style)
- Background: `bg-red-100` → `bg-amber-50` with `border border-amber-200`
- Icon color: `text-red-600` → `text-amber-600`
- Phone number: styled as a tappable button on mobile — large, full-width, green bg, `tel:` link
- "Return to thelandbank.org" link → proper button with border and padding
- Heading: "We're Sorry" → "Unable to Continue" (less emotional, more informational)
- Add reassuring subtext: "This doesn't have to be permanent."

### 3D. Acknowledgment progressive satisfaction
**Files:** `fh/step_acks.html`, `r4r/step_acks.html`, `vip/step_acks.html`, `base.html` (CSS + JS)
- Running counter at top of ack section: "3 of 6 acknowledged" — updates via JS `MutationObserver` or simple `change` event listener on checkboxes
- Counter style: small pill badge, program-colored
- Checkbox check animation: the checkmark SVG inside the native checkbox won't animate, but the `.ack-card` border transition can be enhanced: `border-color` transition over 200ms with a brief `box-shadow` glow that fades
- When ALL checked: submit button transforms — remove muted appearance, add `box-shadow: 0 0 12px rgba(46,125,50,0.25)` glow pulse that repeats gently (2s cycle)
- JS: listen for change events on all `.ack-card input`, count checked, update counter, toggle submit glow class

### 3E. Document upload success animation
**Files:** `v2/_document_capture.html`, `base.html` (CSS)
- Checkmark SVG in the preview bar: animate with `stroke-dasharray` / `stroke-dashoffset` trick
  - Initial: `stroke-dasharray: 24; stroke-dashoffset: 24` (invisible)
  - On reveal: `stroke-dashoffset: 0` with `transition: stroke-dashoffset 300ms ease`
- Filename text: `@keyframes fadeSlideRight { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: translateX(0); } }` — 200ms, 100ms delay after check animation

### 3F. Info card left-accent treatment
**Files:** `base.html` (CSS), various step templates
- New CSS class `.info-card-accent`:
  ```
  border-left: 3px solid;
  border-radius: 0.75rem;
  padding-left: 1rem;
  ```
- Blue info cards: `border-left-color: #2d6a8a` (replaces current bg-tint-only)
- Green closing info: `border-left-color: #2e7d32`
- Maintains existing background tint but adds structural weight via the left border
- Icon gets a small colored circle background (like section label icons)

---

## Implementation Notes

### Constraints
- All CSS-only where possible — no new JS libraries
- JS limited to: `IntersectionObserver` (scroll reveal), checkbox counters, offer formatting
- No changes to Django views, models, URLs, or form classes
- Tailwind Play CDN — all custom CSS in `base.html` `<style>` block
- Must not break existing HTMX behaviors
- `maximum-scale=1` preserved (iOS zoom prevention)

### Testing Checklist
- [ ] Mobile Safari iOS — fixed bottom bar doesn't conflict with Safari's own bottom bar
- [ ] Chrome Android — all animations perform at 60fps
- [ ] Desktop Firefox — backdrop-filter fallback (solid bg) works
- [ ] Screen reader — animated elements don't interfere with focus order
- [ ] Slow connection — page is usable before animations load (progressive enhancement)
- [ ] All 3 program paths (FH cash, FH land contract, R4R, VIP) render correctly
- [ ] Confirmation page confetti doesn't block interaction
- [ ] Fixed bottom bar doesn't overlap form content

### Accessibility Notes
- All animations respect `prefers-reduced-motion: reduce` — add media query to disable
- Confetti is decorative (`aria-hidden="true"`)
- Ack counter is a `role="status"` live region for screen readers
- Fixed bottom bar has sufficient contrast against page content
- Touch targets remain 44px minimum throughout
