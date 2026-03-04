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
from .htmx import (
    htmx_down_payment_minimum,
    htmx_intended_use_fields,
    htmx_progress_bar,
    htmx_properties_json,
    htmx_property_search,
    htmx_purchase_type_fields,
    htmx_renovation_totals,
    htmx_self_employed_label,
)
from .documents import document_view
from .submission import confirmation_page
from .shared import (
    resume_draft,
    save_progress,
)

__all__ = [
    # Accordion views
    "apply_page",
    "section_program_select",
    "section_validate",
    "section_edit",
    "disqualified",
    # HTMX partials
    "htmx_purchase_type_fields",
    "htmx_intended_use_fields",
    "htmx_renovation_totals",
    "htmx_self_employed_label",
    "htmx_down_payment_minimum",
    "htmx_progress_bar",
    "htmx_properties_json",
    "htmx_property_search",
    # Save & resume
    "save_progress",
    "resume_draft",
    # Confirmation
    "confirmation_page",
    # Staff document access
    "document_view",
]
