"""
URL patterns for the buyer-facing application form.

V1 (wizard): Steps 1-3 have fixed URLs, steps 4+ use dispatcher.
V2 (accordion): Single page at /apply/v2/ with HTMX section endpoints.
HTMX endpoints are shared between both versions.
"""

from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    # ── V2 accordion flow ────────────────────────────────────────
    path("v2/", views.apply_page, name="apply_page"),
    path(
        "v2/section/<str:section_id>/validate/",
        views.section_validate,
        name="section_validate",
    ),
    path(
        "v2/section/<str:section_id>/edit/",
        views.section_edit,
        name="section_edit",
    ),
    path(
        "v2/section/program-select/",
        views.section_program_select,
        name="section_program_select",
    ),
    path("v2/disqualified/", views.disqualified, name="disqualified_v2"),
    # ── V1 shared steps (1-3) ────────────────────────────────────
    path("", views.step_identity, name="step_identity"),
    path("property/", views.step_property, name="step_property"),
    path("eligibility/", views.step_eligibility, name="step_eligibility"),
    # ── V1 program-specific steps (4+) ───────────────────────────
    path("step/<int:step_num>/", views.program_step, name="program_step"),
    # ── HTMX partial endpoints (shared) ──────────────────────────
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
    # ── Save & resume ────────────────────────────────────────────
    path("save/", views.save_progress, name="save_progress"),
    path("resume/<uuid:token>/", views.resume_draft, name="resume"),
]
