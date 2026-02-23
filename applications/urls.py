"""
URL patterns for the buyer-facing application form.

Single-page accordion at /apply/ with HTMX section endpoints.
"""

from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    # ── Accordion flow ──────────────────────────────────────────
    path("", views.apply_page, name="apply_page"),
    path(
        "section/<str:section_id>/validate/",
        views.section_validate,
        name="section_validate",
    ),
    path(
        "section/<str:section_id>/edit/",
        views.section_edit,
        name="section_edit",
    ),
    path(
        "section/program-select/",
        views.section_program_select,
        name="section_program_select",
    ),
    path("disqualified/", views.disqualified, name="disqualified_v2"),
    # ── HTMX partial endpoints ──────────────────────────────────
    path(
        "htmx/purchase-type-fields/",
        views.htmx_purchase_type_fields,
        name="htmx_purchase_type_fields",
    ),
    path(
        "htmx/intended-use-fields/",
        views.htmx_intended_use_fields,
        name="htmx_intended_use_fields",
    ),
    path(
        "htmx/renovation-totals/",
        views.htmx_renovation_totals,
        name="htmx_renovation_totals",
    ),
    path(
        "htmx/self-employed-label/",
        views.htmx_self_employed_label,
        name="htmx_self_employed_label",
    ),
    path(
        "htmx/down-payment-min/",
        views.htmx_down_payment_minimum,
        name="htmx_down_payment_minimum",
    ),
    path(
        "htmx/progress-bar/",
        views.htmx_progress_bar,
        name="htmx_progress_bar",
    ),
    # ── Confirmation ────────────────────────────────────────────
    path(
        "confirmation/<str:ref>/",
        views.confirmation_page,
        name="confirmation",
    ),
    # ── Save & resume ────────────────────────────────────────────
    path("save/", views.save_progress, name="save_progress"),
    path("resume/<uuid:token>/", views.resume_draft, name="resume"),
    # ── Staff document access (pre-signed URLs) ──────────────────
    path(
        "documents/<int:document_id>/view/",
        views.document_view,
        name="document_view",
    ),
]
