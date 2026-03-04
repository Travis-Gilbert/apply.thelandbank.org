"""
HTMX partial endpoints for dynamic form behavior.

These views return HTML fragments (not full pages) for HTMX to
swap into the DOM. They're called via hx-get or hx-post from the
buyer-facing form templates.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


def htmx_purchase_type_fields(request):
    """
    Swap in/out the land contract fields (down payment, self-employed)
    based on the selected purchase type.

    Triggered by: hx-get on purchase_type radio buttons
    Target: #purchase-type-fields container
    """
    purchase_type = request.GET.get("purchase_type", "cash")
    show_land_contract = purchase_type == "land_contract"
    return render(
        request,
        "apply/partials/purchase_type_fields.html",
        {"show_land_contract": show_land_contract},
    )


def htmx_intended_use_fields(request):
    """
    Show/hide the 'first home or moving' sub-question based on intended use.

    Triggered by: hx-get on intended_use select
    Target: #intended-use-sub container
    """
    intended_use = request.GET.get("intended_use", "")
    show_sub_question = intended_use == "renovate_move_in"
    return render(
        request,
        "apply/partials/intended_use_sub.html",
        {"show_sub_question": show_sub_question},
    )


def htmx_renovation_totals(request):
    """
    Calculate and return renovation subtotals and total as the buyer types.

    Triggered by: hx-post on each line-item input (debounced)
    Returns: updated subtotal/total display fragment

    Uses the same field lists as the Application model to ensure
    consistency between client-side preview and server-side storage.
    """
    from ..models import Application

    interior_total = Decimal("0")
    for field_name in Application.INTERIOR_RENO_FIELDS:
        val = request.POST.get(field_name, "0")
        try:
            interior_total += Decimal(val) if val else Decimal("0")
        except InvalidOperation:
            pass

    exterior_total = Decimal("0")
    for field_name in Application.EXTERIOR_RENO_FIELDS:
        val = request.POST.get(field_name, "0")
        try:
            exterior_total += Decimal(val) if val else Decimal("0")
        except InvalidOperation:
            pass

    grand_total = interior_total + exterior_total

    return render(
        request,
        "apply/partials/renovation_totals.html",
        {
            "interior_subtotal": f"{interior_total:,.2f}",
            "exterior_subtotal": f"{exterior_total:,.2f}",
            "reno_total": f"{grand_total:,.2f}",
        },
    )


def htmx_down_payment_minimum(request):
    """
    Calculate and show the minimum down payment as the buyer types.

    Triggered by: hx-get on offer_amount or down_payment_amount change
    Target: #down-payment-min container
    """
    offer_raw = request.GET.get("offer_amount", "0")
    try:
        offer = Decimal(offer_raw) if offer_raw else Decimal("0")
    except InvalidOperation:
        offer = Decimal("0")

    if offer > 0:
        min_down = max(offer * Decimal("0.10"), Decimal("1000.00"))
        return HttpResponse(
            f'<p class="text-xs text-civic-blue-700 font-mono mt-1">'
            f"Minimum down payment: ${min_down:,.2f} "
            f"(10% of offer or $1,000, whichever is higher)</p>"
        )
    return HttpResponse("")


def htmx_progress_bar(request):
    """
    Return updated progress bar data after program/purchase type selection.

    Triggered by: hx-get on program_type or purchase_type radio change
    Target: #progress-bar container (or full sidebar re-render)
    """
    from ..routing import get_all_steps

    program_type = request.GET.get("program_type", "featured_homes")
    purchase_type = request.GET.get("purchase_type", "cash")
    all_steps = get_all_steps(program_type, purchase_type)
    total = len(all_steps)

    return HttpResponse(
        f'<span class="text-[11px] font-mono text-warm-500 flex-shrink-0">'
        f"2/{total}</span>"
    )


@ratelimit(key="ip", rate="30/m", method="GET", block=True)
def htmx_properties_json(request):
    """
    Return all available properties as JSON for client-side search.

    Called once on page load; the browser filters locally on every keystroke.
    Excludes vacant_lot (program not yet implemented).
    """
    from ..models import Property
    from .accordion import PROGRAM_META

    props = list(
        Property.objects.filter(status="available")
        .exclude(program_type="vacant_lot")
        .values("id", "address", "parcel_id", "program_type", "address_normalized")
    )
    for p in props:
        meta = PROGRAM_META.get(p["program_type"], {})
        p["program_name"] = meta.get("name", p["program_type"])
        p["program_color"] = meta.get("color", "#666")

    return JsonResponse(props, safe=False)


@ratelimit(key="ip", rate="30/m", method="GET", block=True)
def htmx_property_search(request):
    """
    HTMX autocomplete: search available properties by address or parcel ID.

    Triggered by: hx-get on property_address input (debounced 300ms)
    Target: #property-results container
    Returns: dropdown of matching properties, or empty if < 3 chars
    """
    from ..models import Property

    q = request.GET.get("property_address", "").strip()
    if len(q) < 3:
        return HttpResponse("")

    # Try address match first (normalized for fuzzy matching)
    # Exclude vacant_lot - program not yet implemented, buyers would hit dead end
    try:
        normalized = Property.normalize_address(q)
        results = list(
            Property.objects.filter(
                status="available",
                address_normalized__icontains=normalized,
            )
            .exclude(program_type="vacant_lot")[:8]
        )

        # Fall back to parcel ID match if no address hits
        if not results:
            results = list(
                Property.objects.filter(
                    status="available",
                    parcel_id__icontains=q,
                )
                .exclude(program_type="vacant_lot")[:8]
            )
    except Exception:
        logger.exception("Property search failed for query: %s", q)
        return render(
            request,
            "apply/partials/property_results.html",
            {"error": True, "query": q},
        )

    # Import here to avoid circular import at module level
    from .accordion import PROGRAM_META

    # Build display-friendly results
    for r in results:
        meta = PROGRAM_META.get(r.program_type, {})
        r.program_name = meta.get("name", r.program_type)
        r.program_color = meta.get("color", "#666")

    return render(
        request,
        "apply/partials/property_results.html",
        {"results": results, "query": q},
    )


def htmx_self_employed_label(request):
    """
    Swap income document label based on self-employed checkbox.

    Triggered by: hx-get on is_self_employed checkbox
    Target: #income-doc-label container
    """
    is_self_employed = request.GET.get("is_self_employed") == "true"
    if is_self_employed:
        label = "Tax returns (last 2 years)"
        help_text = "Self-employed applicants must provide tax returns instead of pay stubs."
    else:
        label = "Pay stubs (last 60 days)"
        help_text = "Upload your two most recent pay stubs."

    return render(
        request,
        "apply/partials/self_employed_label.html",
        {
            "income_label": label,
            "income_help_text": help_text,
            "is_self_employed": is_self_employed,
        },
    )
