"""
Accordion view — single-page collapsible application flow.

Replaces the multi-page wizard with an HTMX-powered accordion where
only one section is expanded at a time. Completed sections collapse
into compact summary bars. Future sections are hidden until reached.

Architecture:
  - apply_page: GET renders initial page (program section expanded)
  - section_validate: POST validates a section, returns collapsed summary + next expanded
  - section_edit: GET re-expands a completed section for editing
  - section_program_select: POST handles program card click
  - submit_application_v2: POST final submission from acks section
"""

import os
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .. import forms as app_forms
from ..models import ApplicationDraft
from .shared import _get_draft

# ── Program metadata ────────────────────────────────────────────────

PROGRAM_META = {
    "featured_homes": {
        "name": "Featured Homes",
        "icon": "",
        "icon_svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2E7D32" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "tagline": "Move-in ready homes at affordable prices",
        "description": "Homes available for immediate sale",
        "note": "Cash or land contract. All homes sold as-is.",
        "time": "10-15 minutes",
        "color": "#2E7D32",
        "color_light": "#E8F5E9",
    },
    "ready_for_rehab": {
        "name": "Ready for Rehab",
        "icon": "",
        "icon_svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F57C00" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M15 12l-8.5 8.5c-.83.83-2.17.83-3 0s-.83-2.17 0-3L12 9"/><path d="M17.64 15L22 10.64"/><path d="m20.91 11.7-1.25-1.25c-.6-.6-.93-1.4-.93-2.25V6.5L15.5 4H12l-2 2v3l2.5 3h1.7c.85 0 1.65.33 2.25.93l1.25 1.25"/></svg>',
        "tagline": "Homes that need renovation at lower costs",
        "description": "As-is homes sold at lower purchase prices",
        "note": "Cash only. Detailed cost estimates required.",
        "time": "15-20 minutes",
        "color": "#F57C00",
        "color_light": "#FFF3E0",
    },
    "vip_spotlight": {
        "name": "VIP Spotlight",
        "icon": "",
        "icon_svg": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1565C0" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></svg>',
        "tagline": "Unique properties evaluated by proposal",
        "description": "Select properties reviewed by proposal",
        "note": "Scored on plan, experience, financing, and neighborhood benefit.",
        "time": "20-30 minutes",
        "color": "#1565C0",
        "color_light": "#E3F2FD",
    },
}

# ── Section definitions ─────────────────────────────────────────────
#
# Each section maps to a form class (or None for document uploads) and
# template paths for expanded + collapsed states.
#
# Section order is dynamic — determined by program_type + purchase_type.

SECTION_DEFS = {
    "property_search": {
        "title": "Find Your Property",
        "form": "PropertySearchForm",
        "expanded_template": "apply/v2/sections/property_search_expanded.html",
        "collapsed_template": "apply/v2/sections/property_search_collapsed.html",
    },
    # Legacy — kept for backwards compat with old drafts
    "program": {
        "title": "Select a Program",
        "form": None,
        "expanded_template": "apply/v2/sections/program_expanded.html",
        "collapsed_template": "apply/v2/sections/program_collapsed.html",
    },
    "contact": {
        "title": "Contact Information",
        "form": "IdentityForm",
        "expanded_template": "apply/v2/sections/contact_expanded.html",
        "collapsed_template": "apply/v2/sections/contact_collapsed.html",
    },
    "property": {
        "title": "Property Information",
        "form": "PropertyForm",
        "expanded_template": "apply/v2/sections/property_expanded.html",
        "collapsed_template": "apply/v2/sections/property_collapsed.html",
    },
    "eligibility": {
        "title": "Eligibility",
        "form": "EligibilityForm",
        "expanded_template": "apply/v2/sections/eligibility_expanded.html",
        "collapsed_template": "apply/v2/sections/eligibility_collapsed.html",
    },
    "offer": {
        "title": "Offer Details",
        "form": {
            "featured_homes": "FHOfferForm",
            "ready_for_rehab": "R4ROfferForm",
        },
        "expanded_template": {
            "featured_homes": "apply/v2/sections/fh/offer_expanded.html",
            "ready_for_rehab": "apply/v2/sections/r4r/offer_expanded.html",
        },
        "collapsed_template": {
            "featured_homes": "apply/v2/sections/fh/offer_collapsed.html",
            "ready_for_rehab": "apply/v2/sections/r4r/offer_collapsed.html",
        },
    },
    "documents": {
        "title": "Documents",
        "form": None,  # Document upload, no form class
        "is_documents": True,
        "expanded_template": {
            "featured_homes": "apply/v2/sections/fh/documents_expanded.html",
            "ready_for_rehab": "apply/v2/sections/r4r/documents_expanded.html",
            "vip_spotlight": "apply/v2/sections/vip/documents_expanded.html",
        },
        "collapsed_template": {
            "featured_homes": "apply/v2/sections/fh/documents_collapsed.html",
            "ready_for_rehab": "apply/v2/sections/r4r/documents_collapsed.html",
            "vip_spotlight": "apply/v2/sections/vip/documents_collapsed.html",
        },
    },
    "line_items": {
        "title": "Renovation Estimate",
        "form": "R4RLineItemsForm",
        "expanded_template": "apply/v2/sections/r4r/line_items_expanded.html",
        "collapsed_template": "apply/v2/sections/r4r/line_items_collapsed.html",
    },
    "renovation": {
        "title": "Renovation Plan",
        "form": {
            "featured_homes": "FHRenovationNarrativeForm",
            "ready_for_rehab": "R4RRenovationNarrativeForm",
        },
        "expanded_template": {
            "featured_homes": "apply/v2/sections/fh/renovation_expanded.html",
            "ready_for_rehab": "apply/v2/sections/r4r/renovation_expanded.html",
        },
        "collapsed_template": {
            "featured_homes": "apply/v2/sections/fh/renovation_collapsed.html",
            "ready_for_rehab": "apply/v2/sections/r4r/renovation_collapsed.html",
        },
    },
    "homebuyer_ed": {
        "title": "Homebuyer Education",
        "form": "FHHomebuyerEdForm",
        "expanded_template": "apply/v2/sections/fh/homebuyer_ed_expanded.html",
        "collapsed_template": "apply/v2/sections/fh/homebuyer_ed_collapsed.html",
    },
    "proposal": {
        "title": "Proposal",
        "form": "VIPProposalForm",
        "expanded_template": "apply/v2/sections/vip/proposal_expanded.html",
        "collapsed_template": "apply/v2/sections/vip/proposal_collapsed.html",
    },
    "acks": {
        "title": "Review & Submit",
        "form": {
            "featured_homes": "FHAcknowledgmentsForm",
            "ready_for_rehab": "R4RAcknowledgmentsForm",
            "vip_spotlight": "VIPAcknowledgmentsForm",
        },
        "expanded_template": {
            "featured_homes": "apply/v2/sections/fh/acks_expanded.html",
            "ready_for_rehab": "apply/v2/sections/r4r/acks_expanded.html",
            "vip_spotlight": "apply/v2/sections/vip/acks_expanded.html",
        },
        # acks never collapses — it's always the last section
    },
}


# ── Section order by program ────────────────────────────────────────

SECTION_ORDER = {
    ("featured_homes", "cash"): [
        "property_search", "contact", "eligibility",
        "offer", "documents", "renovation", "acks",
    ],
    ("featured_homes", "land_contract"): [
        "property_search", "contact", "eligibility",
        "offer", "documents", "renovation", "homebuyer_ed", "acks",
    ],
    ("ready_for_rehab", "cash"): [
        "property_search", "contact", "eligibility",
        "offer", "documents", "line_items", "renovation", "acks",
    ],
    ("vip_spotlight", "cash"): [
        "property_search", "contact", "eligibility",
        "proposal", "documents", "acks",
    ],
}

# Before property/program is determined, show only the property search
DEFAULT_SECTION_ORDER = ["property_search"]


def _get_section_order(program_type, purchase_type="cash"):
    """Get the section order for a program + purchase type combo."""
    if not program_type:
        return DEFAULT_SECTION_ORDER
    key = (program_type, purchase_type)
    return SECTION_ORDER.get(key, SECTION_ORDER.get((program_type, "cash"), DEFAULT_SECTION_ORDER))


# ── Template resolution ─────────────────────────────────────────────

def _resolve_template(section_def, template_key, program_type):
    """Resolve a template path — handles dict (per-program) or string (shared)."""
    tmpl = section_def.get(template_key)
    if isinstance(tmpl, dict):
        return tmpl.get(program_type, tmpl.get("featured_homes"))
    return tmpl


def _resolve_form_class(section_def, program_type):
    """Resolve a form class — handles dict (per-program) or string (shared)."""
    form_name = section_def.get("form")
    if isinstance(form_name, dict):
        form_name = form_name.get(program_type)
    if form_name:
        return getattr(app_forms, form_name)
    return None


# ── Summary builders ────────────────────────────────────────────────

def _build_summary(section_id, form_data):
    """Build a one-line summary string for a collapsed section."""
    if section_id == "property_search":
        addr = form_data.get("property_address", "")
        program_type = form_data.get("program_type", "")
        meta = PROGRAM_META.get(program_type, {})
        program_name = meta.get("name", "")
        if addr and program_name:
            return f"{addr} \u00b7 {program_name}"
        return addr or program_name

    # Legacy handlers for old drafts
    if section_id == "program":
        program_type = form_data.get("program_type", "")
        meta = PROGRAM_META.get(program_type, {})
        return meta.get("name", program_type)

    if section_id == "contact":
        first = form_data.get("first_name", "")
        last = form_data.get("last_name", "")
        entity = form_data.get("purchasing_entity_name", "")
        email = form_data.get("email", "")
        parts = [f"{first} {last}".strip()]
        if entity:
            parts[0] += f" ({entity})"
        if email:
            parts.append(email)
        return " \u00b7 ".join(parts)

    if section_id == "property":
        addr = form_data.get("property_address", "")
        parcel = form_data.get("parcel_id", "")
        if parcel:
            return f"{addr} \u00b7 {parcel}"
        return addr

    if section_id == "eligibility":
        return "Eligible to apply"

    if section_id == "offer":
        amount = form_data.get("offer_amount", "")
        ptype = form_data.get("purchase_type", "cash")
        label = "Land Contract" if ptype == "land_contract" else "Cash"
        if amount:
            try:
                amount_fmt = f"${Decimal(amount):,.0f}"
            except Exception:
                amount_fmt = f"${amount}"
            return f"{amount_fmt} \u00b7 {label}"
        return label

    if section_id == "line_items":
        total = form_data.get("total_renovation_cost", "")
        if total:
            try:
                return f"Estimated total: ${Decimal(total):,.0f}"
            except Exception:
                return f"Estimated total: ${total}"
        return "Renovation estimate provided"

    if section_id == "renovation":
        use = form_data.get("intended_use", "")
        use_labels = {
            "renovate_move_in": "Renovate and move in",
            "renovate_family": "Renovate for family member",
            "renovate_sell": "Renovate and sell",
            "renovate_rent": "Renovate and rent out",
            "demolish": "Demolish",
        }
        label = use_labels.get(use, use)
        return f"{label} \u00b7 Plans provided" if label else "Renovation plans provided"

    if section_id == "homebuyer_ed":
        agency = form_data.get("homebuyer_ed_agency", "")
        agency_labels = {
            "metro_community_dev": "Metro Community Development",
            "habitat_for_humanity": "Genesee County Habitat for Humanity",
            "fannie_mae_online": "Fannie Mae (online)",
            "other": form_data.get("homebuyer_ed_other", "Other"),
        }
        return f"Homebuyer education: {agency_labels.get(agency, agency)}"

    if section_id == "proposal":
        return "Proposal submitted"

    if section_id == "documents":
        uploads = form_data.get("uploads", {})
        count = len(uploads)
        if count == 1:
            return "1 document uploaded"
        return f"{count} documents uploaded"

    return ""


# ── Shared context builder ──────────────────────────────────────────

def _section_context(draft, section_id, section_number, program_type, purchase_type):
    """Build the context dict for rendering a section template."""
    form_data = draft.form_data or {}
    meta = PROGRAM_META.get(program_type, PROGRAM_META["featured_homes"])
    section_def = SECTION_DEFS[section_id]
    section_order = _get_section_order(program_type, purchase_type)
    total_sections = len(section_order)

    ctx = {
        "section_id": section_id,
        "section_number": section_number,
        "section_title": section_def["title"],
        "program_type": program_type,
        "purchase_type": purchase_type,
        "program_color": meta["color"],
        "program_color_light": meta["color_light"],
        "program_name": meta["name"],
        "program_icon": meta["icon"],
        "form_data": form_data,
        "draft": draft,
        "total_sections": total_sections,
        "completed_count": section_number - 1,
        # URLs for HTMX
        "validate_url": reverse("applications:section_validate", args=[section_id]),
        "edit_url": reverse("applications:section_edit", args=[section_id]),
    }

    # Property search needs program metadata for info cards and fallback picker
    if section_id == "property_search":
        ctx["programs"] = PROGRAM_META

    return ctx


# ── Main page view ──────────────────────────────────────────────────

def apply_page(request):
    """
    GET /apply/ — render the accordion page.

    On first visit: shows only the property search section (expanded).
    On resume: rebuilds collapsed summaries for completed sections,
    expands the current section.
    """
    draft = _get_draft(request)
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type")
    purchase_type = form_data.get("purchase_type", "cash")

    section_order = _get_section_order(program_type, purchase_type)
    meta = PROGRAM_META.get(program_type, PROGRAM_META["featured_homes"])

    # Determine which section is active (first incomplete section)
    # Map draft.current_step to accordion section index
    active_index = _draft_step_to_section_index(draft, section_order)

    # Build the list of sections to render
    sections = []
    for i, section_id in enumerate(section_order):
        section_def = SECTION_DEFS[section_id]
        if i < active_index:
            # Completed — render as collapsed summary bar
            sections.append({
                "id": section_id,
                "state": "collapsed",
                "number": i + 1,
                "title": section_def["title"],
                "summary": _build_summary(section_id, form_data),
                "edit_url": reverse("applications:section_edit", args=[section_id]),
            })
        elif i == active_index:
            # Active — render as expanded section with form
            form_instance = _build_form_for_section(section_id, program_type, form_data)
            expanded = {
                "id": section_id,
                "state": "expanded",
                "number": i + 1,
                "title": section_def["title"],
                "form": form_instance,
                "template": _resolve_template(section_def, "expanded_template", program_type),
                "validate_url": reverse("applications:section_validate", args=[section_id]),
            }
            # Property search needs program metadata for cards and info display
            if section_id == "property_search":
                expanded["programs"] = PROGRAM_META
            sections.append(expanded)
        # Future sections: not rendered at all

    ctx = {
        "sections": sections,
        "program_type": program_type,
        "purchase_type": purchase_type,
        "program_color": meta["color"] if program_type else "#2E7D32",
        "program_name": meta["name"] if program_type else None,
        "programs": PROGRAM_META,
        "completed_count": active_index,
        "total_sections": len(section_order),
        "form_data": form_data,
        "draft": draft,
    }
    return render(request, "apply/v2/apply_page.html", ctx)


# ── Program selection ────────────────────────────────────────────────

def section_program_select(request):
    """
    POST — handles program card click.

    Saves the selected program, returns the collapsed program summary bar
    + the expanded contact section via hx-swap-oob.
    """
    if request.method != "POST":
        return redirect("applications:apply_page")

    draft = _get_draft(request)
    form_data = draft.form_data or {}
    program_key = request.POST.get("program")

    if program_key not in PROGRAM_META:
        return redirect("applications:apply_page")

    form_data["program_type"] = program_key
    # Default purchase type for initial selection
    if program_key == "ready_for_rehab":
        form_data["purchase_type"] = "cash"
    elif program_key == "vip_spotlight":
        form_data["purchase_type"] = "cash"
    else:
        form_data.setdefault("purchase_type", "cash")

    draft.form_data = form_data
    draft.program_type = program_key
    draft.current_step = max(draft.current_step, 2)
    draft.save()

    purchase_type = form_data.get("purchase_type", "cash")
    meta = PROGRAM_META[program_key]
    section_order = _get_section_order(program_key, purchase_type)

    # Build collapsed program summary
    program_summary_html = render(
        request,
        "apply/v2/sections/program_collapsed.html",
        {
            "section_id": "program",
            "program_type": program_key,
            "program_color": meta["color"],
            "program_name": meta["name"],
            "program_icon": "",
            "summary_text": meta["name"],
            "edit_url": reverse("applications:section_edit", args=["program"]),
        },
    ).content.decode()

    # Build expanded contact section
    contact_form = app_forms.IdentityForm(initial=form_data)
    contact_ctx = _section_context(draft, "contact", 2, program_key, purchase_type)
    contact_ctx["form"] = contact_form
    contact_html = render(
        request,
        "apply/v2/sections/contact_expanded.html",
        contact_ctx,
    ).content.decode()

    # Build progress bar
    progress_html = render(
        request,
        "apply/v2/_progress_bar.html",
        {
            "completed_count": 1,
            "total_count": len(section_order),
            "program_color": meta["color"],
            "program_name": meta["name"],
        },
    ).content.decode()

    # Combine: primary response replaces accordion container
    html = f"""
    <div id="section-program" class="accordion-section accordion-gap">
        {program_summary_html}
    </div>
    <div id="section-contact" class="accordion-section accordion-gap-active">
        {contact_html}
    </div>
    <div id="progress-bar" hx-swap-oob="innerHTML">
        {progress_html}
    </div>
    """
    return HttpResponse(html)


# ── Section validation ───────────────────────────────────────────────

def section_validate(request, section_id):
    """
    POST — validate a section's form data.

    On success: saves to draft, returns collapsed summary + expanded next section.
    On failure: returns the section re-rendered with validation errors.
    """
    if request.method != "POST":
        return redirect("applications:apply_page")

    draft = _get_draft(request)
    form_data = draft.form_data or {}

    # Property search is special — it determines the program, which affects
    # everything downstream.  Handle it before we resolve section_order.
    if section_id == "property_search":
        return _validate_property_search_section(request, draft)

    program_type = form_data.get("program_type", "featured_homes")
    purchase_type = form_data.get("purchase_type", "cash")
    section_order = _get_section_order(program_type, purchase_type)
    meta = PROGRAM_META.get(program_type, PROGRAM_META["featured_homes"])

    if section_id not in section_order:
        return redirect("applications:apply_page")

    section_index = section_order.index(section_id)
    section_number = section_index + 1
    section_def = SECTION_DEFS[section_id]

    # Handle document upload sections
    if section_def.get("is_documents"):
        return _validate_documents_section(
            request, draft, section_id, section_index, section_order,
            program_type, purchase_type, meta
        )

    # Handle eligibility gate specially
    if section_id == "eligibility":
        return _validate_eligibility_section(
            request, draft, section_index, section_order,
            program_type, purchase_type, meta
        )

    # Resolve and validate form
    form_class = _resolve_form_class(section_def, program_type)
    if not form_class:
        return redirect("applications:apply_page")

    form = form_class(request.POST)

    if form.is_valid():
        cleaned = _serialize_cleaned_data(form.cleaned_data)

        # Special handling for R4R line items
        if section_id == "line_items":
            totals = form.calculate_totals()
            cleaned.update({k: str(v) for k, v in totals.items()})

        # R4R offer: force cash
        if program_type == "ready_for_rehab" and section_id == "offer":
            cleaned["purchase_type"] = "cash"

        # FH offer: purchase_type may change section order
        if section_id == "offer" and program_type == "featured_homes":
            new_ptype = cleaned.get("purchase_type", purchase_type)
            if new_ptype != purchase_type:
                purchase_type = new_ptype
                section_order = _get_section_order(program_type, purchase_type)
                form_data["purchase_type"] = purchase_type

        form_data.update(cleaned)
        draft.form_data = form_data

        # Check if this is the last section (acks = submit)
        if section_id == "acks":
            # Guard: verify all required documents before allowing submission
            from .shared import _get_required_docs
            uploads = form_data.get("uploads", {})
            required_docs = _get_required_docs(program_type, purchase_type, form_data)
            missing = [d for d in required_docs if d not in uploads]
            if missing:
                # Save form data but do NOT advance current_step
                draft.save()
                doc_labels = {
                    "photo_id": "Photo ID",
                    "proof_of_funds": "Proof of Funds",
                    "proof_of_income": "Proof of Income",
                    "proof_of_down_payment": "Proof of Down Payment",
                    "reno_funding_proof": "Renovation Funding Documentation",
                    "prior_investment_proof": "Prior GCLBA Investment Proof",
                }
                names = [doc_labels.get(d, d.replace("_", " ").title()) for d in missing]
                ctx = _section_context(draft, section_id, section_number, program_type, purchase_type)
                ctx["form"] = form
                ctx["doc_errors"] = ["Missing required documents: " + ", ".join(names) + ". Please go back to the Documents section to upload them."]
                template = _resolve_template(section_def, "expanded_template", program_type)
                return _render_expanded_response(request, template, ctx, section_id)

            # Docs present — advance step and submit
            overall_step = section_index + 1  # 1-indexed
            draft.current_step = max(draft.current_step, overall_step + 1)
            draft.save()
            from .submission import submit_application
            return submit_application(request, draft)

        # Non-acks sections: advance step normally
        overall_step = section_index + 1  # 1-indexed
        draft.current_step = max(draft.current_step, overall_step + 1)
        draft.save()

        return _render_transition(
            request, draft, section_id, section_index, section_order,
            program_type, purchase_type, meta
        )

    # Validation failed — re-render expanded section with errors
    ctx = _section_context(draft, section_id, section_number, program_type, purchase_type)
    ctx["form"] = form
    template = _resolve_template(section_def, "expanded_template", program_type)
    return _render_expanded_response(request, template, ctx, section_id)


def _validate_eligibility_section(
    request, draft, section_index, section_order,
    program_type, purchase_type, meta
):
    """Handle eligibility gate — disqualify if needed."""
    form_data = draft.form_data or {}
    form = app_forms.EligibilityForm(request.POST)

    if form.is_valid():
        cleaned = form.cleaned_data
        has_taxes = cleaned["has_delinquent_taxes"] == "yes"
        has_foreclosure = cleaned["has_tax_foreclosure"] == "yes"

        form_data["has_delinquent_taxes"] = has_taxes
        form_data["has_tax_foreclosure"] = has_foreclosure
        draft.form_data = form_data
        draft.save()

        if has_taxes or has_foreclosure:
            # Disqualified — full-page redirect via HX-Redirect
            response = HttpResponse()
            response["HX-Redirect"] = reverse("applications:disqualified_v2")
            return response

        draft.current_step = max(draft.current_step, section_index + 2)
        draft.save()

        return _render_transition(
            request, draft, "eligibility", section_index, section_order,
            program_type, purchase_type, meta
        )

    # Validation failed
    ctx = _section_context(draft, "eligibility", section_index + 1, program_type, purchase_type)
    ctx["form"] = form
    return _render_expanded_response(
        request, "apply/v2/sections/eligibility_expanded.html", ctx, "eligibility"
    )


def _validate_property_search_section(request, draft):
    """
    Handle property search validation — the opening section.

    This is special because it determines the program, which affects the
    entire section order for the rest of the application.  After validation:
    1. Sets program_type + purchase_type on the draft
    2. Resolves the full section order
    3. Returns collapsed property_search + expanded contact section
    """
    form_data = draft.form_data or {}
    form = app_forms.PropertySearchForm(request.POST)

    if form.is_valid():
        cleaned = _serialize_cleaned_data(form.cleaned_data)
        program_type = cleaned["program_type"]

        # Set default purchase type (may change later in the offer section)
        if program_type == "ready_for_rehab":
            purchase_type = "cash"
        elif program_type == "vip_spotlight":
            purchase_type = "cash"
        else:
            purchase_type = "cash"

        form_data.update(cleaned)
        form_data["purchase_type"] = purchase_type
        draft.form_data = form_data
        draft.program_type = program_type
        draft.current_step = max(draft.current_step, 2)
        draft.save()

        meta = PROGRAM_META[program_type]
        section_order = _get_section_order(program_type, purchase_type)

        return _render_transition(
            request, draft, "property_search", 0, section_order,
            program_type, purchase_type, meta
        )

    # Validation failed — re-render with errors
    ctx = _section_context(
        draft, "property_search", 1,
        form_data.get("program_type", ""),
        form_data.get("purchase_type", "cash"),
    )
    ctx["form"] = form
    ctx["programs"] = PROGRAM_META
    return _render_expanded_response(
        request, "apply/v2/sections/property_search_expanded.html",
        ctx, "property_search"
    )


def _validate_documents_section(
    request, draft, section_id, section_index, section_order,
    program_type, purchase_type, meta
):
    """Handle document upload validation."""
    from .shared import (
        ALLOWED_EXTENSIONS,
        ALLOWED_MIME_TYPES,
        MAX_UPLOAD_SIZE,
        _get_optional_docs,
        _get_required_docs,
    )

    form_data = draft.form_data or {}
    required_docs = _get_required_docs(program_type, purchase_type, form_data)
    optional_docs = _get_optional_docs(program_type)
    all_doc_types = required_docs + optional_docs

    uploaded = form_data.get("uploads", {}).copy()
    file_errors = {}
    draft_prefix = f"drafts/{draft.token}"

    for doc_type in all_doc_types:
        file = request.FILES.get(doc_type)
        if file:
            # Validate
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                file_errors[doc_type] = f'"{file.name}" is not an accepted file type.'
                continue
            if file.content_type not in ALLOWED_MIME_TYPES:
                file_errors[doc_type] = f'"{file.name}" has an unrecognized format.'
                continue
            if file.size > MAX_UPLOAD_SIZE:
                size_mb = file.size / (1024 * 1024)
                file_errors[doc_type] = f'"{file.name}" is {size_mb:.1f} MB. Max is 10 MB.'
                continue

            safe_name = "".join(c for c in file.name if c.isalnum() or c in ".-_") or "upload"
            dest_path = f"{draft_prefix}/{doc_type}_{safe_name}"
            saved_path = default_storage.save(dest_path, file)
            uploaded[doc_type] = {
                "filename": file.name,
                "path": saved_path,
            }

    missing_docs = [d for d in required_docs if d not in uploaded]

    form_data["uploads"] = uploaded
    draft.form_data = form_data
    draft.save()

    errors = list(file_errors.values())
    if missing_docs:
        doc_labels = {
            "photo_id": "Photo ID",
            "proof_of_funds": "Proof of Funds",
            "proof_of_income": "Proof of Income",
            "proof_of_down_payment": "Proof of Down Payment",
            "reno_funding_proof": "Renovation Funding Documentation",
            "prior_investment_proof": "Prior GCLBA Investment Proof",
        }
        names = [doc_labels.get(d, d.replace("_", " ").title()) for d in missing_docs]
        errors.append("Missing required documents: " + ", ".join(names))

    if not errors:
        draft.current_step = max(draft.current_step, section_index + 2)
        draft.save()
        return _render_transition(
            request, draft, section_id, section_index, section_order,
            program_type, purchase_type, meta
        )

    # Re-render with errors
    section_def = SECTION_DEFS[section_id]
    ctx = _section_context(draft, section_id, section_index + 1, program_type, purchase_type)
    ctx.update({
        "required_docs": required_docs,
        "optional_docs": optional_docs,
        "uploaded": uploaded,
        "errors": errors,
        "has_file_upload": True,
    })
    template = _resolve_template(section_def, "expanded_template", program_type)
    return _render_expanded_response(request, template, ctx, section_id)


# ── Section edit (re-expand) ─────────────────────────────────────────

def section_edit(request, section_id):
    """
    GET — re-expand a completed section for editing.

    Returns the expanded section HTML. The accordion JS handles
    collapsing whatever was previously active.
    """
    draft = _get_draft(request)
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "featured_homes")
    purchase_type = form_data.get("purchase_type", "cash")
    section_order = _get_section_order(program_type, purchase_type)
    meta = PROGRAM_META.get(program_type, PROGRAM_META["featured_homes"])

    if section_id not in section_order:
        return redirect("applications:apply_page")

    section_index = section_order.index(section_id)
    section_number = section_index + 1
    section_def = SECTION_DEFS[section_id]

    # Special case: property_search edit returns the search form with existing data
    if section_id == "property_search":
        form_instance = _build_form_for_section("property_search", program_type, form_data)
        ctx = _section_context(draft, "property_search", 1, program_type, purchase_type)
        ctx["form"] = form_instance
        ctx["programs"] = PROGRAM_META
        return _render_expanded_response(
            request, "apply/v2/sections/property_search_expanded.html",
            ctx, "property_search"
        )

    # Legacy: program edit returns the selector (for old drafts)
    if section_id == "program":
        ctx = {
            "section_id": "program",
            "programs": PROGRAM_META,
            "program_type": program_type,
            "program_color": meta["color"],
            "select_url": reverse("applications:section_program_select"),
        }
        return _render_expanded_response(
            request, "apply/v2/sections/program_expanded.html", ctx, "program"
        )

    # Build form from draft data
    form_instance = _build_form_for_section(section_id, program_type, form_data)

    ctx = _section_context(draft, section_id, section_number, program_type, purchase_type)
    ctx["form"] = form_instance

    # For document sections, add doc-specific context
    if section_def.get("is_documents"):
        from .shared import _get_optional_docs, _get_required_docs
        ctx.update({
            "required_docs": _get_required_docs(program_type, purchase_type, form_data),
            "optional_docs": _get_optional_docs(program_type),
            "uploaded": form_data.get("uploads", {}),
            "has_file_upload": True,
        })

    template = _resolve_template(section_def, "expanded_template", program_type)
    response = _render_expanded_response(request, template, ctx, section_id)

    # Collapse the currently active section (if different from the one being edited)
    active_index = _draft_step_to_section_index(draft, section_order)
    if active_index < len(section_order) and section_order[active_index] != section_id:
        active_section_id = section_order[active_index]
        active_def = SECTION_DEFS[active_section_id]
        collapsed_ctx = {
            "section_id": active_section_id,
            "section_title": active_def["title"],
            "summary_text": _build_summary(active_section_id, form_data),
            "program_color": meta["color"],
            "edit_url": reverse("applications:section_edit", args=[active_section_id]),
        }
        collapsed_tmpl = _resolve_template(active_def, "collapsed_template", program_type)
        collapsed_inner = render(request, collapsed_tmpl, collapsed_ctx).content.decode()
        oob_html = (
            f'<div id="section-{active_section_id}" '
            f'hx-swap-oob="outerHTML:#section-{active_section_id}" '
            f'class="accordion-section accordion-gap">'
            f'{collapsed_inner}</div>'
        )
        # Append OOB swap to the response
        response.content = response.content + oob_html.encode()

    return response


# ── Disqualified page ────────────────────────────────────────────────

def disqualified(request):
    """Render the disqualification page (eligibility gate failure)."""
    return render(request, "apply/disqualified.html")


# ── Helpers ──────────────────────────────────────────────────────────

def _render_transition(
    request, draft, current_section_id, current_index, section_order,
    program_type, purchase_type, meta
):
    """
    Render the collapsed summary of the current section + expanded next section.

    The button's hx-target points to #section-{current_section_id} with
    hx-swap="outerHTML".  We return:
      1. Collapsed summary of current section  (primary swap content)
      2. Expanded next section                 (primary swap content)
      3. Progress bar                          (hx-swap-oob — element exists)

    Items 1+2 are the PRIMARY response (no hx-swap-oob) so HTMX replaces
    the old expanded section with both elements via outerHTML.  The next
    section doesn't need to pre-exist in the DOM.

    Neither collapsed nor expanded templates include the outer
    <div id="section-..."> wrapper — that's always added here.
    """
    form_data = draft.form_data or {}
    section_def = SECTION_DEFS[current_section_id]

    # Collapsed summary for current section
    collapsed_ctx = {
        "section_id": current_section_id,
        "section_title": section_def["title"],
        "summary_text": _build_summary(current_section_id, form_data),
        "program_color": meta["color"],
        "edit_url": reverse("applications:section_edit", args=[current_section_id]),
    }
    collapsed_template = _resolve_template(section_def, "collapsed_template", program_type)
    collapsed_inner = render(request, collapsed_template, collapsed_ctx).content.decode()
    # Collapsed templates render only the inner summary-bar — add the id wrapper
    collapsed_html = (
        f'<div id="section-{current_section_id}" '
        f'class="accordion-section accordion-gap">'
        f'{collapsed_inner}</div>'
    )

    # Next section (expanded)
    next_index = current_index + 1
    next_section_html = ""
    if next_index < len(section_order):
        next_section_id = section_order[next_index]
        next_section_def = SECTION_DEFS[next_section_id]
        next_number = next_index + 1

        next_form = _build_form_for_section(next_section_id, program_type, form_data)
        next_ctx = _section_context(
            draft, next_section_id, next_number, program_type, purchase_type
        )
        next_ctx["form"] = next_form

        # Document sections need extra context
        if next_section_def.get("is_documents"):
            from .shared import _get_optional_docs, _get_required_docs
            next_ctx.update({
                "required_docs": _get_required_docs(program_type, purchase_type, form_data),
                "optional_docs": _get_optional_docs(program_type),
                "uploaded": form_data.get("uploads", {}),
                "has_file_upload": True,
            })

        next_template = _resolve_template(next_section_def, "expanded_template", program_type)
        next_inner = render(request, next_template, next_ctx).content.decode()
        # Expanded templates don't include the outer id wrapper — add it here
        next_section_html = (
            f'<div id="section-{next_section_id}" '
            f'class="accordion-section accordion-gap-active">'
            f'{next_inner}</div>'
        )

    # Progress bar update (OOB — this element already exists in the DOM)
    progress_html = render(
        request,
        "apply/v2/_progress_bar.html",
        {
            "completed_count": next_index,
            "total_count": len(section_order),
            "program_color": meta["color"],
            "program_name": meta["name"],
        },
    ).content.decode()

    # Assemble response:
    # - Collapsed + next section are PRIMARY content (replace hx-target via outerHTML)
    # - Progress bar is OOB (updates existing #progress-bar element)
    html = collapsed_html + next_section_html
    html += (
        f'<div id="progress-bar" hx-swap-oob="innerHTML:#progress-bar">'
        f'{progress_html}</div>'
    )

    response = HttpResponse(html)
    # Trigger scroll to next section
    if next_index < len(section_order):
        response["HX-Trigger"] = f'{{"scrollToSection": "section-{section_order[next_index]}"}}'
    return response


def _render_expanded_response(request, template, ctx, section_id):
    """Render an expanded section wrapped in its outer ``#section-{id}`` div.

    All HTMX responses that return an expanded section must include the
    outer wrapper so that subsequent ``hx-target="#section-..."`` lookups
    still work after ``outerHTML`` swap.
    """
    inner = render(request, template, ctx).content.decode()
    gap = "" if section_id in ("program", "property_search") else " accordion-gap-active"
    html = (
        f'<div id="section-{section_id}" '
        f'class="accordion-section{gap}">'
        f'{inner}</div>'
    )
    return HttpResponse(html)


def _build_form_for_section(section_id, program_type, form_data):
    """Build a form instance pre-populated from draft data for a section."""
    section_def = SECTION_DEFS.get(section_id, {})
    form_class = _resolve_form_class(section_def, program_type)
    if not form_class:
        return None

    initial = {}
    blank_form = form_class()
    for field_name in blank_form.fields:
        if field_name in form_data:
            initial[field_name] = form_data[field_name]
    return form_class(initial=initial)


def _draft_step_to_section_index(draft, section_order):
    """
    Map the draft's current_step to the corresponding accordion section index.

    The draft stores current_step as "the next step to work on" (1-indexed).
    After completing section at index ``i``, the validators set
    ``current_step = max(current_step, i + 2)`` — that is, index+1 (to
    make it 1-indexed) plus 1 (to advance to the *next* step).

    So the reverse mapping is simply ``section_index = step - 1``.
    """
    step = draft.current_step or 1

    if not draft.form_data or not draft.form_data.get("program_type"):
        return 0  # No program selected yet — show program selector

    # Program (index 0) is always completed if we have a program_type,
    # so the earliest valid section is index 1 (contact).
    section_index = max(1, step - 1)

    # Clamp to valid range
    return min(section_index, len(section_order) - 1)


def _serialize_cleaned_data(cleaned_data):
    """Convert form cleaned_data to JSON-safe types for draft storage."""
    result = {}
    for key, value in cleaned_data.items():
        if isinstance(value, Decimal):
            result[key] = str(value)
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result
