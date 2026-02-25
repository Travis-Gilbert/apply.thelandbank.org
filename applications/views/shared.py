"""
Shared utilities for the accordion application flow:
  - Draft management (get/create/resume)
  - Save & resume with magic link email
  - Document upload constants and helpers
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django_ratelimit.decorators import ratelimit

from ..models import ApplicationDraft

logger = logging.getLogger(__name__)


# ── Document upload constraints ──────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


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


# ── Draft helpers ─────────────────────────────────────────────────


def _get_draft(request):
    """Get or create the current session's draft."""
    draft_token = request.session.get("draft_token")
    if draft_token:
        try:
            draft = ApplicationDraft.objects.get(token=draft_token)
            # If the draft was already submitted, clear it and start fresh
            if draft.submitted:
                request.session.pop("draft_token", None)
            elif not draft.is_expired:
                return draft
        except ApplicationDraft.DoesNotExist:
            pass
    draft = ApplicationDraft.objects.create()
    request.session["draft_token"] = str(draft.token)
    return draft


# ── Save & Resume ────────────────────────────────────────────────


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def save_progress(request):
    """Save current progress and send magic link email."""
    draft = _get_draft(request)

    if not draft.email:
        return HttpResponse(
            '<span class="text-amber-600">'
            "Please complete your contact information first to save your progress.</span>"
        )

    resume_url = request.build_absolute_uri(f"/apply/resume/{draft.token}/")
    context = {
        "first_name": draft.form_data.get("first_name", ""),
        "property_address": draft.form_data.get("property_address", "your property"),
        "resume_url": resume_url,
        "expires_at": draft.expires_at.strftime("%B %d, %Y"),
    }

    try:
        send_mail(
            subject="Continue Your GCLBA Application",
            message=render_to_string("emails/magic_link.txt", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[draft.email],
            html_message=render_to_string("emails/magic_link.html", context),
        )
    except Exception:
        logger.exception("Failed to send magic link email to %s", draft.email)
        return HttpResponse(
            '<span class="text-amber-600">'
            "Progress saved, but we couldn't send the email. "
            "Please try again or note your application link.</span>"
        )

    return HttpResponse(
        '<span class="text-civic-green-700 font-medium">'
        "&#10003; Progress saved! Check your email for a resume link.</span>"
    )


def resume_draft(request, token):
    """Resume a draft from a magic link."""
    draft = get_object_or_404(ApplicationDraft, token=token)

    if draft.submitted:
        from ..models import Application

        app = Application.objects.filter(email=draft.email).order_by("-submitted_at").first()
        return render(request, "apply/already_submitted.html", {
            "reference_number": app.reference_number if app else None,
            "email": draft.email,
        })

    if draft.is_expired:
        return render(request, "apply/link_expired.html")

    # Restore session and redirect to the accordion page (it rebuilds state from draft)
    request.session["draft_token"] = str(draft.token)
    return redirect("applications:apply_page")
