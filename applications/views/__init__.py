"""
Views package for the GCLBA buyer-facing application form.

Re-exports all view functions for use in urls.py.
"""

from .accordion import (
    apply_page,
    disqualified,
    section_edit,
    section_program_select,
    section_validate,
)
from .dispatcher import program_step
from .htmx import (
    htmx_down_payment_minimum,
    htmx_intended_use_fields,
    htmx_progress_bar,
    htmx_purchase_type_fields,
    htmx_renovation_totals,
    htmx_self_employed_label,
)
from .documents import document_view
from .shared import (
    resume_draft,
    save_progress,
    step_eligibility,
    step_identity,
    step_property,
)

__all__ = [
    # Shared steps (v1 wizard)
    "step_identity",
    "step_property",
    "step_eligibility",
    # Program dispatcher (v1 wizard)
    "program_step",
    # Accordion views (v2)
    "apply_page",
    "section_program_select",
    "section_validate",
    "section_edit",
    "disqualified",
    # HTMX partials (shared)
    "htmx_purchase_type_fields",
    "htmx_intended_use_fields",
    "htmx_renovation_totals",
    "htmx_self_employed_label",
    "htmx_down_payment_minimum",
    "htmx_progress_bar",
    # Save & resume
    "save_progress",
    "resume_draft",
    # Staff document access
    "document_view",
]
