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
from django.shortcuts import redirect, render
from django.utils import timezone

from .. import forms as app_forms
from ..models import Application, ApplicationDraft, Document
from ..routing import get_program_steps
from .shared import _get_draft, _step_context
from .submission import submit_application


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

    step_def = program_steps[step_num - 1]
    overall_step = step_num + 3  # shared steps are 1-3

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


def _handle_documents_step(
    request, draft, step_def, step_num, overall_step, program_type, purchase_type
):
    """Handle document upload steps (no form class)."""
    form_data = draft.form_data or {}
    required_docs = _get_required_docs(program_type, purchase_type, form_data)

    if request.method == "POST":
        uploaded = {}
        upload_dir = os.path.join(settings.MEDIA_ROOT, "drafts", str(draft.token))
        os.makedirs(upload_dir, exist_ok=True)

        all_uploaded = True
        for doc_type in required_docs:
            file = request.FILES.get(doc_type)
            if file:
                file_path = os.path.join(upload_dir, f"{doc_type}_{file.name}")
                with open(file_path, "wb+") as dest:
                    for chunk in file.chunks():
                        dest.write(chunk)
                uploaded[doc_type] = {
                    "filename": file.name,
                    "path": file_path,
                }
            elif form_data.get("uploads", {}).get(doc_type):
                uploaded[doc_type] = form_data["uploads"][doc_type]
            else:
                all_uploaded = False

        form_data["uploads"] = uploaded
        draft.form_data = form_data
        draft.save()

        if all_uploaded:
            draft.current_step = overall_step + 1
            draft.save()
            return redirect("applications:program_step", step_num=step_num + 1)

        # Re-render with error
        ctx = _step_context(draft, overall_step)
        ctx.update({
            "step_title": step_def["title"],
            "required_docs": required_docs,
            "optional_docs": _get_optional_docs(program_type),
            "uploaded": uploaded,
            "error": "Please upload all required documents.",
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
        "optional_docs": _get_optional_docs(program_type),
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
