# GCLBA Application Portal — CLAUDE.md

## What This Is

A property purchase application portal for the Genesee County Land Bank Authority (GCLBA)
in Flint, MI. Replaces a manual process where buyers download PDF forms, email incomplete
packets to offers@thelandbank.org, and staff chase down missing documents.

The portal has two surfaces:
- **Buyer-facing:** Program-specific multi-step application with save-and-return, document
  uploads, and email confirmation on submission
- **Staff-facing:** Review dashboard built on django-unfold where Alex's sales team can
  see all incoming applications, their status, and attached documents

Alex Riley (Director) is the primary stakeholder. She has been asking for this for years
and nobody has delivered it. Build it well.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Django 6.0.2 | Built-in admin, forms, auth, migrations |
| Admin theme | django-unfold | Modern Tailwind-based replacement for Django Admin |
| Buyer forms | Custom Django views + Tailwind CSS + HTMX | Server-rendered, HTMX for conditional field logic |
| Database | PostgreSQL (Railway) | Prod DB via Railway plugin |
| File storage | Django Storages + S3 or Backblaze B2 | Secure document storage, pre-signed URLs for staff viewing |
| Email | SendGrid or Resend | Confirmation on submission, staff notification |
| Deployment | Railway | Auto-deploy from GitHub, Postgres built in |
| Auth | Django built-in | Staff login; buyers use UUID magic links, no account required |

**Do not use React.** Server-rendered with HTMX for conditional logic only.

---

## CRITICAL: Four Programs, Four Different Form Paths

This is NOT one unified form. Program selection at Step 2 determines which fields,
documents, and sections appear. Each program has materially different requirements.

### Program Comparison

| | Featured Homes | Ready for Rehab | VIP Spotlight | Vacant Lot |
|--|--|--|--|--|
| Purchase types | Cash, Land Contract | Cash ONLY | Proposal process | TBD |
| Land Contract available | Yes | No | No | No |
| Renovation estimate | Narrative only | Line-item breakdown required | Narrative + timeline | N/A |
| Scoring | Highest offer + funding | Highest offer + funding + reno plan | Price, Feasibility, Experience, Financing, Neighborhood Benefit | TBD |
| Prior GCLBA purchase proof | No | Yes (if applicable) | Portfolio required | TBD |

---

## Program-Specific Requirements

### Featured Homes

**Purchase types:** Cash only OR Land Contract only. No conventional, FHA, or VA.

**Land Contract rules:**
- Owner-occupied ONLY — land contract not available for rental or investment intent
- Minimum down payment: 10% of offer amount OR $1,000, whichever is higher
- Validate server-side AND show client-side via HTMX
- Homebuyer education course required before closing (MSHDA or HUD approved counselor)
- Closing fee: $125 (vs $75 for cash)

**Document requirements:**

Cash:
- Valid photo ID (state-issued, driver's license, military ID, passport — NO student IDs, NO non-picture IDs)
- Proof of available funds for full offer amount

Land Contract:
- Valid photo ID (same restrictions)
- Proof of income: pay stubs last 60 days OR tax returns if self-employed
- Proof of available funds for down payment amount (not full offer amount)

**Renovation section (all Featured Homes buyers):**
- Intended use: Renovate & Move In / Renovate for Family Member / Renovate & Sell / Renovate & Rent Out / Demolish
- If "Renovate & Move In": sub-question shown via HTMX: First home purchase / Moving to MI from another state / Neither
- What renovations will you be making? (textarea)
- Who will complete renovations? (textarea)
- When will renovations be completed? (text)
- How will you pay for purchase and renovations? (textarea)

**Closing info (read-only, informational display):**
- Payment due in full at closing via cashier's check or money order
- Closing within 21 days of offer acceptance
- Quit Claim Deed, no title insurance provided by GCLBA

---

### Ready for Rehab

**Purchase type:** Cash ONLY. No land contract option for this program.

**Documents required:**
- Valid photo ID (same restrictions as above)
- Proof of available funds for offer amount
- Proof of available funds OR financing documentation for estimated renovation costs
- Proof of investment in previously purchased GCLBA property (conditional — only if applicant has purchased from GCLBA before)

**Prior GCLBA purchase fields:**
```
has_prior_gclba_purchase    BooleanField ("Have you previously purchased from GCLBA?")
doc_prior_investment        FileField, required if has_prior_gclba_purchase=True
```

**Renovation estimate — LINE ITEM BREAKDOWN REQUIRED:**

R4R applicants must fill out individual cost estimates for each trade. Auto-calculate
subtotals and total using HTMX as user types. Store all line items plus calculated totals.

Interior Costs (all DecimalField, default=0):
- Clean out
- Demolition & Disposal
- HVAC
- Water heater
- Plumbing
- Electrical
- Kitchen Cabinets
- Kitchen Appliances
- Bathroom Repairs
- Flooring & Floor Covering
- Doors
- Insulation
- Drywall & Plaster
- Paint & Wallpaper
- Lighting
- Interior Subtotal (calculated, stored)

Exterior Costs (all DecimalField, default=0):
- Clean up & Landscaping
- Roof
- Foundation
- Doors
- Windows
- Siding
- Masonry
- Porch or Decking
- Lighting
- Garage Repair or Demolition
- Exterior Subtotal (calculated, stored)

Total Renovation Costs (calculated: Interior + Exterior, stored)

Same intended use and narrative questions as Featured Homes apply here too.

**Note for staff:** A Renovation Cost Guide exists with typical Flint cost ranges.
Staff reference it when evaluating whether R4R renovation estimates are realistic.
Typical ranges: electrical $2,500-3,800 / furnace $3,000-3,500 / roof $350-550/sq /
foundation $360/linear ft / windows $500-600 each / drywall $12/sq ft.

---

### VIP Spotlight

**This is a proposal process, not a standard offer form.**

VIP properties are unique or historically significant homes evaluated on multiple
criteria, not just price. The applicant submits a written proposal answering 8
structured questions. There is no standard offer amount field — purchase price is
stated within the proposal narrative.

**VIP Proposal Questions (all text areas, all required unless noted):**

1. Who are you and why do you want to purchase this property? Include proposed purchase
   price, contact info, and buyer/entity name.
2. Have you purchased single-family homes from GCLBA previously? (BooleanField + textarea)
3. What are your estimated renovation costs and development timeline? (Detailed scope requested)
4. How do you intend to finance the project? Include proof of funds for equity portion
   and pre-approval letters for construction loans if applicable.
5. Do you have single-family home renovation experience? (BooleanField + textarea asking for
   portfolio: addresses of renovated homes, before/after photos)
6. What are your plans upon completion — sell or rent? (ChoiceField + textarea)
7. Will you hire a contractor? If so, provide names and Genesee County experience. (optional)
8. Any additional information — letters of support, references, community ties. (optional)

**VIP Scoring Criteria (display to applicant so they understand how they're evaluated):**
Price / Feasibility of Project / Experience / Financing / Neighborhood Benefit /
Local Individuals or Businesses (Genesee County residency or business registration earns bonus points)

**VIP Documents:**
- Valid photo ID
- Proof of funds (equity portion minimum)
- Pre-approval letter (if using construction financing) — optional
- Portfolio photos of past renovations — optional (required if experience claimed in Q5)
- Letters of support — optional, multiple allowed

**VIP Legal acknowledgments (additional beyond standard):**
- 5/50 Tax Capture: buyer acknowledges waiver request must be made before offer acceptance.
  Seeking Brownfield or other abatements without a waiver conflicts with 5/50 tax roll.
- Reconveyance Deed: buyer acknowledges signing reconveyance deed at closing. Property
  reverts to GCLBA if project not completed per Purchase & Development Agreement.
- No transfer or encumbrance of property without prior written GCLBA consent until
  Release of Interest is recorded.

**VIP form path is entirely separate from Featured Homes / R4R. Build as its own view set.**

---

### Vacant Lot

Requirements TBD. Build placeholder only in Phase 1. Do not implement.

---

## Full Field Map by Section

### Section 1: Applicant Identity (all programs)
```
first_name              CharField, required
last_name               CharField, required
email                   EmailField, required
phone                   CharField, required
mailing_address         CharField, required
mailing_city            CharField, required
mailing_state           CharField, default="MI"
mailing_zip             CharField, required
preferred_contact       ChoiceField [email, text, phone_call]
purchasing_entity_name  CharField, optional
contact_name_different  CharField, optional
```

### Section 2: Property (all programs)
```
property_address        CharField, required
parcel_id               CharField, optional
program_type            ChoiceField [featured_homes, ready_for_rehab, vip, vacant_lot]
attended_open_house     BooleanField, required
open_house_date         DateField, required if attended_open_house=True
```

### Section 3: Eligibility Gate (all programs — hard block)
```
has_delinquent_taxes    BooleanField, required
had_tax_foreclosure     BooleanField, required
```
If either True: redirect to disqualified.html. Use exact GCLBA language:
"The Land Bank cannot sell to you if you have delinquent property taxes or if you
have been through tax foreclosure with the Genesee County Treasurer in the last
five years."

### Section 4: Offer Details (Featured Homes + R4R only)
```
offer_amount            DecimalField, required
purchase_type           ChoiceField:
                          Featured Homes: [cash, land_contract]
                          Ready for Rehab: not shown (cash only, set automatically)
down_payment_amount     DecimalField, required if purchase_type=land_contract
                        Server-side validation:
                          min_down = max(offer_amount * 0.10, 1000.00)
                          raise ValidationError if down_payment < min_down
is_self_employed        BooleanField, shown if purchase_type=land_contract
                        Changes income document label via HTMX
```

### Section 5: Documents (program + purchase type conditional — see above)

### Section 6: Renovation (program-specific — see above)

### Section 7: Land Contract / Homebuyer Education (Featured Homes land contract only)
```
homebuyer_ed_completed  BooleanField
homebuyer_ed_agency     ChoiceField [metro_community_dev, habitat_for_humanity,
                                     fannie_mae_online, other]
homebuyer_ed_other      CharField, shown if agency=other
```
Display info: "Required before closing. Metro Community Development 810-767-4622 /
Genesee County Habitat for Humanity 810-766-9089 / Fannie Mae (online, free, 3-4 hrs)"

### Section 8: Acknowledgments (all programs)
```
ack_sold_as_is              BooleanField, required
ack_quit_claim_deed         BooleanField, required
ack_no_title_insurance      BooleanField, required
ack_highest_not_guaranteed  BooleanField, required (Featured Homes + R4R)
ack_info_accurate           BooleanField, required
ack_tax_capture             BooleanField, required
                            Label: "I understand any request to waive the Land Bank
                            5/50 tax capture must be made before the Land Bank accepts
                            my offer. Otherwise the request will not be considered."

# VIP only — additional:
ack_reconveyance_deed       BooleanField, required
ack_no_transfer             BooleanField, required
```

---

## Closing Fee Reference (display only, not collected)

| Program | Purchase Type | Closing Fee |
|---------|--------------|-------------|
| Featured Homes | Cash | $75 |
| Featured Homes | Land Contract | $125 |
| Ready for Rehab | Cash | $75 |
| VIP | Any | Per Purchase & Development Agreement |

Display on confirmation page and in staff dashboard detail view.

---

## Step Routing by Program

```
All programs share Steps 1-3:
  Step 1: Identity
  Step 2: Property + Program Selection
  Step 3: Eligibility Gate (disqualify or continue)

Featured Homes — Cash:
  Step 4: Offer Details
  Step 5: Documents
  Step 6: Renovation Narrative
  Step 7: Acknowledgments + Submit

Featured Homes — Land Contract:
  Step 4: Offer Details (with down payment)
  Step 5: Documents (land contract docs)
  Step 6: Renovation Narrative
  Step 7: Homebuyer Education
  Step 8: Acknowledgments + Submit

Ready for Rehab:
  Step 4: Offer Details (cash, no choice)
  Step 5: Documents (R4R docs)
  Step 6: Renovation Line Items
  Step 7: Renovation Narrative + Intended Use
  Step 8: Acknowledgments + Submit

VIP Spotlight:
  Step 4: Proposal Questions (8 questions)
  Step 5: Documents (VIP docs + portfolio)
  Step 6: Acknowledgments (includes VIP-specific) + Submit
```

Progress indicator updates based on actual step count for the buyer's path.
Update via HTMX partial after program selection in Step 2.

---

## Save-and-Return Flow

```python
class ApplicationDraft(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    email = models.EmailField()
    program_type = models.CharField(max_length=50)
    data = models.JSONField(default=dict)
    current_step = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()  # 14 days from creation
    submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
```

Magic link: apply.thelandbank.org/resume/<uuid-token>

---

## Email Triggers

| Event | Recipient | Content |
|-------|-----------|---------|
| Draft saved (step 1 complete) | Buyer | Magic link to resume |
| Final submission | Buyer | Confirmation + reference number + summary |
| Final submission | Staff | New application alert with review link |
| Status: Needs More Info | Buyer | What is needed |
| Status: Approved | Buyer | Next steps + closing info |
| Status: Declined | Buyer | Decline notice |

All templates: HTML + plain text versions required.

---

## Staff Dashboard (django-unfold)

### Application List
Columns: Name / Property / Program / Purchase Type / Offer Amount / Status / Submitted / Docs Complete

Filters: Status / Program / Purchase Type / Date range / Documents complete

### Application Detail
All fields organized by section / Documents (pre-signed URLs, 15-min expiry) /
Status dropdown / Internal staff notes (never visible to buyer) /
Action buttons: Approve / Decline / Request More Info

### Status Workflow + Badge Colors
```
RECEIVED (blue) -> UNDER_REVIEW (amber) -> APPROVED (green)
                                        -> DECLINED (red)
                                        -> NEEDS_MORE_INFO (orange) -> UNDER_REVIEW
```

### Reference Number Format
GCLBA-{YEAR}-{ZERO_PADDED_4_DIGIT}
Generated on final submission only. Example: GCLBA-2026-0001

---

## Design System

### Buyer-Facing
- Civic green: #2e7d32 (primary), civic blue: #2d6a8a (accent)
- Tailwind CSS via Play CDN (no build step, config in base.html `<script>`)
- Fonts: Bitter (headings, `font-heading`), IBM Plex Sans (body, `font-sans`), JetBrains Mono (`font-mono`)
- **font-mono rule:** ONLY on dollar amounts, reference numbers (GCLBA-YYYY-NNNN), property IDs, and numeric inputs. Never on phone numbers, emails, addresses, labels, or time phrases.
- Each step = its own screen with progress bar
- Mobile-first, large touch targets
- Plain language labels throughout — no legal jargon
- HTMX: conditional field reveal, renovation totals, step counter updates
- Renovation line-item totals auto-calculate client-side as user types
- Mobile: `inputmode="decimal"` on money fields, `inputmode="tel"` on phone, `inputmode="numeric"` on ZIP.
  Viewport uses `maximum-scale=1` to prevent iOS auto-zoom. All interactive elements 44px min touch target.

### Staff Dashboard
- django-unfold base theme, primary overridden to #2B6553
- Status badges as above
- Dense table for list view
- Pre-signed document URLs only — never expose raw S3/B2 URLs

---

## Development Commands

```bash
source venv/bin/activate          # Required — python not on PATH without it
python manage.py runserver 8199   # Dev server (port 8199 avoids conflicts)
python manage.py check            # Validate models, urls, templates
python manage.py makemigrations --check  # Verify no missing migrations
```

**Deploy:** merge develop → main, push main (Railway auto-deploys)
**Railway URL:** https://apply-thelandbankorg.up.railway.app/apply/

---

## Deployment

**Platform: Railway** — PostgreSQL plugin, auto-deploy on push to main

**Domain:** apply.thelandbank.org (separate from compliance.thelandbank.org)

**Environment Variables:**
```
DATABASE_URL              # auto-set by Railway
SECRET_KEY                # 50+ random chars
DEBUG                     # False in production
ALLOWED_HOSTS             # apply.thelandbank.org
EMAIL_API_KEY
DEFAULT_FROM_EMAIL        # applications@thelandbank.org
STAFF_NOTIFICATION_EMAIL  # inbox Alex's team monitors
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME
AWS_S3_REGION_NAME
```

---

## Code Patterns

1. **Program routing** — program_type on ApplicationDraft determines which view
   classes and form classes load. Separate form classes per step per program.
   Do not use one giant form with all fields.

2. **Renovation line items** — store individual fields AND calculated subtotals/total
   on Application model. Never recalculate from line items after submission.

3. **Down payment validation** (land contract):
   ```python
   from decimal import Decimal
   min_down = max(offer_amount * Decimal('0.10'), Decimal('1000.00'))
   if down_payment < min_down:
       raise ValidationError(
           f"Minimum down payment is ${min_down:,.2f} "
           f"(10% of offer or $1,000, whichever is higher)"
       )
   ```

4. **Photo ID label** — always display: "State-issued ID, driver's license,
   military ID, or passport only. Student IDs and non-picture IDs are not accepted."

5. **Self-employed HTMX swap** — when is_self_employed toggles, HTMX replaces the
   income document label and help text without page reload.

6. **Document security** — all document access through a Django view that generates
   pre-signed URL with 15-minute expiration. Never expose bucket URLs directly.

7. **Multi-file uploads** — VIP portfolio and support letters: multiple Document
   records linked to the same application, same document_type.

8. **Audit log** — every status change creates StatusLog entry: timestamp, staff user,
   old status, new status, optional note.

9. **Fat models, thin views** — validation, reference number generation, status
   transitions in models.py, not views.py.

10. **Django version** — Django 6.0.2 (current production). Spec originally said 5.2 but 6.0 was released; no breaking changes affect this project.

11. **NullBooleanField + RadioSelect** — choices live on `field.widget.choices`, not `field.choices`. In templates: `{% for value, label in form.my_field.field.widget.choices %}`. Use `|stringformat:"s"` on both sides for checked comparison.

12. **Template-form field alignment** — every `{{ form.field_name }}` in a template must exist on the form class that the dispatcher passes for that step. If a field renders with empty name/id/options, it's missing from the form class.

13. **Tailwind config** — loaded via Play CDN `<script>` in `templates/base.html`, not a build pipeline.
    Custom colors (`civic-green-*`, `civic-blue-*`, `warm-*`), fonts, and utilities are defined in
    the inline `tailwind.config` block. No `tailwind.config.js` or PostCSS.

14. **Plain language** — avoid developer jargon in buyer-facing text. Say "a link to resume your
    application" not "magic link". Say "reference number" not "token". The audience is Flint
    residents buying homes, not developers.

15. **Accordion v2 template structure** — `templates/apply/v2/sections/` uses `{section}_expanded.html` +
    `{section}_collapsed.html` pairs. Program-specific sections live in subdirs: `fh/`, `r4r/`, `vip/`.
    Shared partials (entity dropdown, document capture, progress bar) are `_prefixed` in `templates/apply/v2/`.

16. **Mobile CSS centralized in base.html** — touch targets (`.touch-label`), responsive buttons
    (`.continue-btn`, `.doc-capture-btn-primary`), and breakpoint overrides live in the `<style>` block
    in `base.html`, not scattered across section templates. Section templates just apply class names.

17. **Git branch flow** — Admin → develop → main. Railway auto-deploys from `main`.
    Push all three at once: `git push origin main develop Admin`.

---

## Phase 1 MVP Scope

- [ ] Featured Homes path: cash and land contract sub-paths
- [ ] Ready for Rehab path: line-item renovation estimate
- [ ] VIP Spotlight path: proposal questions
- [ ] Eligibility gate shared across all programs
- [ ] Save-and-return with magic link email
- [ ] Program-specific document requirements enforced before submission
- [ ] Down payment minimum validation for land contract
- [ ] Renovation totals auto-calculated via HTMX
- [ ] Self-employed income label swap via HTMX
- [ ] Submission confirmation email to buyer
- [ ] New application notification to staff
- [ ] django-unfold staff dashboard: list view + detail view
- [ ] Status workflow with staff notes and audit log
- [ ] Pre-signed URLs for staff document access
- [ ] Railway deployment with PostgreSQL

**Not in Phase 1:**
- Vacant Lot program
- FileMaker sync
- Automated status-change emails (staff triggers manually)
- Spanish language version
- Payment processing
- API endpoints

---

## Current Status

| Task | Status | Notes |
|------|--------|-------|
| Document uploads (S3/B2) | Open | File fields exist but no storage backend wired |
| Email (SendGrid/Resend) | Open | django-anymail installed, not configured |
| Wire accordion views to models | Open | Section validators need to save to ApplicationDraft |
| Staff dashboard polish | Open | Basic admin works, needs status badges + doc viewing |

## Next Step

Design upgrade is deployed. Three critical-path items remain for end-to-end MVP:
1. **Document uploads** — wire S3/Backblaze B2 storage backend via django-storages. File fields
   exist on models but no storage configured. Pre-signed URLs needed for staff viewing.
2. **Email integration** — django-anymail with Resend is installed but not configured. Need
   save-and-resume email, submission confirmation, and staff notification templates.
3. **Wire accordion views to models** — `applications/views/accordion.py` section validators
   need to save validated data to `ApplicationDraft` and create `Application` on final submit.

---

## Recent Decisions

| Decision | Why | Date |
|----------|-----|------|
| Django 6.0.2 instead of spec's 5.2 | 6.0 released after spec written; no breaking changes; already deployed | 2026-02-19 |
| Port 8199 for dev server | Avoids conflict with other local services | 2026-02-20 |
| font-mono restricted to numeric data only | Phone/email/address/labels use body font; mono only for $ amounts, ref numbers, PIDs | 2026-02-20 |
| Single-page accordion over multi-step wizard | Better UX: one page, HTMX validates per section, collapsed summaries show progress | 2026-02-20 |
| Warm Civic Craft design: CSS-only textures + frosted glass | Colors (#2e7d32 green, #2d6a8a blue, #d4a843 gold), grid/noise/blur — no image assets, no build tooling | 2026-02-20 |
| Header: full org name over acronym | First-time visitors don't know "GCLBA"; spell out "Genesee County Land Bank Authority" with "Property Application Portal" subtitle | 2026-02-20 |

---

## Source Documents (reference)

All of the following were reviewed and used to build this spec:
- Featured Home Offer Form (PDF, updated 8/23/2023) — both pages
- Ready for Rehab Offer Form (PDF, updated 8/23/2023) — both pages including line-item estimate
- VIP Spotlight Residential Proposal Guidelines (PDF) — both pages including 5/50 and reconveyance
- Ready for Rehab Renovation Cost Guide (PDF — staff reference only)
- Residential Property Interest Form (PDF, 7/17/2019 — predecessor, being replaced)
