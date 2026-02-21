"""
Program step dispatcher — generic view that handles steps 4+ based on
the draft's program type and purchase type.

One view function, multiple paths. The routing registry determines which
form class and template to use for each step number.
"""

import os
import shutil
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import redirect, render
from django.utils import timezone

from .. import forms as app_forms
from ..models import Application, ApplicationDraft, Document
from ..routing import get_program_steps
from .shared import _get_draft, _step_context
from .submission import submit_application

# Document upload constraints
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def program_step(request, step_num):
    """
    Dispatch to the correct form + template for program-specific steps.

    step_num is 1-indexed within the program-specific steps (i.e., step_num=1
    is the first step after eligibility, which is overall step 4).
    """
    draft = _get_draft(request)
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "featured_homes")
    purchase_type = form_data.get("purchase_type", "cash")

    program_steps = get_program_steps(program_type, purchase_type)

    # Validate step_num is in range
    if step_num < 1 or step_num > len(program_steps):
        return redirect("applications:step_identity")

    # Enforce step ordering — can't skip ahead past current_step
    overall_step = step_num + 3  # shared steps are 1-3
    if overall_step > draft.current_step:
        # Redirect to where they actually are
        if draft.current_step <= 1:
            return redirect("applications:step_identity")
        elif draft.current_step == 2:
            return redirect("applications:step_property")
        elif draft.current_step == 3:
            return redirect("applications:step_eligibility")
        else:
            return redirect(
                "applications:program_step", step_num=draft.current_step - 3
            )

    step_def = program_steps[step_num - 1]

    # Document upload steps have no form class
    if step_def.get("is_documents"):
        return _handle_documents_step(
            request, draft, step_def, step_num, overall_step, program_type, purchase_type
        )

    # Resolve form class from string name
    form_class = getattr(app_forms, step_def["form"])

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            cleaned = _serialize_cleaned_data(form.cleaned_data)

            # R4R line items: calculate and store totals
            if step_def["key"] == "line_items":
                totals = form.calculate_totals()
                cleaned.update({k: str(v) for k, v in totals.items()})

            # R4R offer: force purchase_type to cash
            if program_type == "ready_for_rehab" and step_def["key"] == "offer":
                cleaned["purchase_type"] = "cash"

            form_data.update(cleaned)
            draft.form_data = form_data
            draft.save()

            # Check if this is the last step (acknowledgments = submit)
            is_last = step_num == len(program_steps)
            if is_last:
                return submit_application(request, draft)

            # Advance to next program step
            draft.current_step = overall_step + 1
            draft.save()
            return redirect("applications:program_step", step_num=step_num + 1)
    else:
        # Pre-populate form from draft data
        initial = {}
        for field_name in form_class().fields:
            if field_name in form_data:
                initial[field_name] = form_data[field_name]
        form = form_class(initial=initial)

    # Build context
    ctx = _step_context(draft, overall_step)
    ctx.update({
        "form": form,
        "step_title": step_def["title"],
        "step_key": step_def["key"],
        "prev_url": _prev_url(step_num),
        "is_last_step": step_num == len(program_steps),
    })
    return render(request, step_def["template"], ctx)


def _validate_upload(file):
    """
    Validate an uploaded file's type and size.

    Returns None if valid, or an error message string if invalid.
    Checks both file extension and browser-reported MIME type.
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            f'"{file.name}" is not an accepted file type. '
            "Please upload a PDF, JPG, PNG, or HEIC file."
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        return (
            f'"{file.name}" has an unrecognized file format. '
            "Please upload a PDF, JPG, PNG, or HEIC file."
        )
    if file.size > MAX_UPLOAD_SIZE:
        size_mb = file.size / (1024 * 1024)
        return f'"{file.name}" is {size_mb:.1f} MB. Maximum file size is 10 MB.'
    return None


def _handle_documents_step(
    request, draft, step_def, step_num, overall_step, program_type, purchase_type
):
    """Handle document upload steps with file type and size validation."""
    form_data = draft.form_data or {}
    required_docs = _get_required_docs(program_type, purchase_type, form_data)
    optional_docs = _get_optional_docs(program_type)
    all_doc_types = required_docs + optional_docs

    if request.method == "POST":
        uploaded = {}
        file_errors = {}
        draft_prefix = f"drafts/{draft.token}"

        for doc_type in all_doc_types:
            file = request.FILES.get(doc_type)
            if file:
                # Validate before saving
                error = _validate_upload(file)
                if error:
                    file_errors[doc_type] = error
                    continue

                # Sanitize filename: keep only alphanumeric, dots, hyphens, underscores
                safe_name = "".join(
                    c for c in file.name if c.isalnum() or c in ".-_"
                ) or "upload"
                dest_path = f"{draft_prefix}/{doc_type}_{safe_name}"
                saved_path = default_storage.save(dest_path, file)
                uploaded[doc_type] = {
                    "filename": file.name,
                    "path": saved_path,
                }
            elif form_data.get("uploads", {}).get(doc_type):
                # Keep previously uploaded file
                uploaded[doc_type] = form_data["uploads"][doc_type]

        # Check which required docs are still missing
        missing_docs = [d for d in required_docs if d not in uploaded]

        form_data["uploads"] = uploaded
        draft.form_data = form_data
        draft.save()

        # Build combined error message
        errors = []
        if file_errors:
            errors.extend(file_errors.values())
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
            draft.current_step = overall_step + 1
            draft.save()
            return redirect("applications:program_step", step_num=step_num + 1)

        ctx = _step_context(draft, overall_step)
        ctx.update({
            "step_title": step_def["title"],
            "required_docs": required_docs,
            "optional_docs": optional_docs,
            "uploaded": uploaded,
            "errors": errors,
            "prev_url": _prev_url(step_num),
            "has_file_upload": True,
        })
        return render(request, step_def["template"], ctx)

    # GET
    uploaded = form_data.get("uploads", {})
    ctx = _step_context(draft, overall_step)
    ctx.update({
        "step_title": step_def["title"],
        "required_docs": required_docs,
        "optional_docs": optional_docs,
        "uploaded": uploaded,
        "prev_url": _prev_url(step_num),
        "has_file_upload": True,
    })
    return render(request, step_def["template"], ctx)


def _get_required_docs(program_type, purchase_type, form_data):
    """Return list of required document type slugs for the program."""
    docs = ["photo_id"]

    if program_type == "featured_homes":
        if purchase_type == "land_contract":
            docs.extend(["proof_of_income", "proof_of_down_payment"])
        else:
            docs.append("proof_of_funds")
    elif program_type == "ready_for_rehab":
        docs.extend(["proof_of_funds", "reno_funding_proof"])
        if form_data.get("has_prior_gclba_purchase"):
            docs.append("prior_investment_proof")
    elif program_type == "vip_spotlight":
        docs.append("proof_of_funds")

    return docs


def _get_optional_docs(program_type):
    """Return list of optional document type slugs for the program."""
    if program_type == "vip_spotlight":
        return ["vip_preapproval", "vip_portfolio_photo", "vip_support_letter"]
    return []


def _prev_url(step_num):
    """Generate URL for the previous step's back button."""
    if step_num == 1:
        return "/apply/eligibility/"
    return f"/apply/step/{step_num - 1}/"


def _serialize_cleaned_data(cleaned_data):
    """
    Convert cleaned_data values to JSON-safe types for storage in
    ApplicationDraft.form_data (JSONField).

    Decimal -> str, date -> isoformat, bool stays bool.
    """
    result = {}
    for key, value in cleaned_data.items():
        if isinstance(value, Decimal):
            result[key] = str(value)
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result
