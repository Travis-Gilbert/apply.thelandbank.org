"""
HTMX partial endpoints for dynamic form behavior.

These views return HTML fragments (not full pages) for HTMX to
swap into the DOM. They're called via hx-get or hx-post from the
buyer-facing form templates.
"""

from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.shortcuts import render


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
