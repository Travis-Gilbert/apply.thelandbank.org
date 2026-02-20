"""
URL patterns for the buyer-facing application form.

Steps 1-3 have fixed URLs (shared across all programs).
Steps 4+ use a single dispatcher URL with step_num parameter.
HTMX endpoints return HTML fragments for dynamic form behavior.
"""

from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    # ── Shared steps (1-3) ────────────────────────────────────────
    path("", views.step_identity, name="step_identity"),
    path("property/", views.step_property, name="step_property"),
    path("eligibility/", views.step_eligibility, name="step_eligibility"),
    # ── Program-specific steps (4+) ───────────────────────────────
    path("step/<int:step_num>/", views.program_step, name="program_step"),
    # ── HTMX partial endpoints ────────────────────────────────────
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
    # ── Save & resume ─────────────────────────────────────────────
    path("save/", views.save_progress, name="save_progress"),
    path("resume/<uuid:token>/", views.resume_draft, name="resume"),
]
