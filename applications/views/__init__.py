"""
Views package for the GCLBA buyer-facing application form.

Re-exports all view functions for use in urls.py.
"""

from .dispatcher import program_step
from .htmx import (
    htmx_down_payment_minimum,
    htmx_intended_use_fields,
    htmx_progress_bar,
    htmx_purchase_type_fields,
    htmx_renovation_totals,
    htmx_self_employed_label,
)
from .shared import (
    resume_draft,
    save_progress,
    step_eligibility,
    step_identity,
    step_property,
)

__all__ = [
    # Shared steps
    "step_identity",
    "step_property",
    "step_eligibility",
    # Program dispatcher
    "program_step",
    # HTMX partials
    "htmx_purchase_type_fields",
    "htmx_intended_use_fields",
    "htmx_renovation_totals",
    "htmx_self_employed_label",
    "htmx_down_payment_minimum",
    "htmx_progress_bar",
    # Save & resume
    "save_progress",
    "resume_draft",
]
