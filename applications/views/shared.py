"""
Shared views for steps 1-3 (Identity, Property, Eligibility) plus
save/resume functionality.

These steps are identical across all four program paths.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from ..forms import EligibilityForm, IdentityForm, PropertyForm
from ..models import ApplicationDraft
from ..routing import get_all_steps, get_total_steps

logger = logging.getLogger(__name__)


# ── Draft helpers ─────────────────────────────────────────────────


def _get_draft(request):
    """Get or create the current session's draft."""
    draft_token = request.session.get("draft_token")
    if draft_token:
        try:
            draft = ApplicationDraft.objects.get(token=draft_token)
            if not draft.is_expired:
                return draft
        except ApplicationDraft.DoesNotExist:
            pass
    draft = ApplicationDraft.objects.create()
    request.session["draft_token"] = str(draft.token)
    return draft


def _step_context(draft, step_number):
    """
    Build progress bar context.

    Uses the draft's program_type and purchase_type to determine
    the correct total step count for the progress indicator.
    """
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "featured_homes")
    purchase_type = form_data.get("purchase_type", "cash")

    all_steps = get_all_steps(program_type, purchase_type)
    total = len(all_steps)

    return {
        "current_step": step_number,
        "total_steps": total,
        "step_range": range(1, total + 1),
        "steps": all_steps,
    }


# ── Step 1: Identity ─────────────────────────────────────────────


def step_identity(request):
    """Step 1: Applicant Identity — creates or resumes draft."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = IdentityForm(request.POST)
        if form.is_valid():
            form_data.update(form.cleaned_data)
            draft.form_data = form_data
            draft.email = form.cleaned_data["email"]
            draft.current_step = 2
            draft.save()
            return redirect("applications:step_property")
    else:
        form = IdentityForm(initial=form_data)

    ctx = _step_context(draft, 1)
    ctx.update({
        "form": form,
        "step_title": "Your Information",
    })
    return render(request, "apply/step_identity.html", ctx)


# ── Step 2: Property & Program Selection ─────────────────────────


def step_property(request):
    """Step 2: Property Information + Program Selection."""
    draft = _get_draft(request)

    # Must complete step 1 before accessing step 2
    if draft.current_step < 2:
        return redirect("applications:step_identity")

    form_data = draft.form_data or {}

    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if cleaned.get("open_house_date"):
                cleaned["open_house_date"] = cleaned["open_house_date"].isoformat()
            form_data.update(cleaned)
            draft.form_data = form_data
            draft.program_type = cleaned["program_type"]
            draft.current_step = 3
            draft.save()
            return redirect("applications:step_eligibility")
    else:
        form = PropertyForm(initial=form_data)

    ctx = _step_context(draft, 2)
    ctx.update({
        "form": form,
        "step_title": "Property & Program",
        "prev_url": "/apply/",
    })
    return render(request, "apply/step_property.html", ctx)


# ── Step 3: Eligibility Gate ─────────────────────────────────────


def step_eligibility(request):
    """Step 3: Eligibility gate — hard block if disqualified."""
    draft = _get_draft(request)

    # Must complete step 2 before accessing step 3
    if draft.current_step < 3:
        if draft.current_step < 2:
            return redirect("applications:step_identity")
        return redirect("applications:step_property")

    form_data = draft.form_data or {}

    if request.method == "POST":
        form = EligibilityForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            has_taxes = cleaned["has_delinquent_taxes"] == "yes"
            has_foreclosure = cleaned["has_tax_foreclosure"] == "yes"

            form_data["has_delinquent_taxes"] = has_taxes
            form_data["has_tax_foreclosure"] = has_foreclosure
            draft.form_data = form_data
            draft.save()

            if has_taxes or has_foreclosure:
                return render(request, "apply/disqualified.html")

            draft.current_step = 4
            draft.save()
            return redirect("applications:program_step", step_num=1)
    else:
        initial = {}
        if "has_delinquent_taxes" in form_data:
            initial["has_delinquent_taxes"] = "yes" if form_data["has_delinquent_taxes"] else "no"
        if "has_tax_foreclosure" in form_data:
            initial["has_tax_foreclosure"] = "yes" if form_data["has_tax_foreclosure"] else "no"
        form = EligibilityForm(initial=initial)

    ctx = _step_context(draft, 3)
    ctx.update({
        "form": form,
        "step_title": "Eligibility",
        "prev_url": "/apply/property/",
    })
    return render(request, "apply/step_eligibility.html", ctx)


# ── Save & Resume ────────────────────────────────────────────────


def save_progress(request):
    """Save current progress and send magic link email."""
    draft = _get_draft(request)

    if not draft.email:
        return HttpResponse(
            '<span class="text-amber-600">'
            "Please complete Step 1 first to save your progress.</span>"
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
        # Draft was already submitted — show the confirmation info
        from ..models import Application

        app = Application.objects.filter(email=draft.email).order_by("-submitted_at").first()
        return render(request, "apply/already_submitted.html", {
            "reference_number": app.reference_number if app else None,
            "email": draft.email,
        })

    if draft.is_expired:
        return render(request, "apply/link_expired.html")

    request.session["draft_token"] = str(draft.token)

    step = draft.current_step
    if step <= 1:
        return redirect("applications:step_identity")
    elif step == 2:
        return redirect("applications:step_property")
    elif step == 3:
        return redirect("applications:step_eligibility")
    else:
        # Steps 4+ are program-specific, mapped as step_num 1+ in the dispatcher
        program_step_num = step - 3
        return redirect("applications:program_step", step_num=program_step_num)
