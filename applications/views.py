"""
Views for the GCLBA multi-step buyer application form.

Flow:
1. apply_start → creates draft, shows Step 1
2. Steps 2-8 → store data in draft.form_data, advance step
3. Conditional skip logic → Steps 6 and 7 may be skipped
4. apply_submit → converts draft to Application + Documents
5. save_progress → sends magic link email for resume
6. resume_draft → restores session from magic link
"""

import os
import shutil
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    Step1IdentityForm,
    Step2PropertyForm,
    Step3OfferForm,
    Step4EligibilityForm,
    Step6RehabForm,
    Step7LandContractForm,
    Step8AcknowledgmentsForm,
)
from .models import Application, ApplicationDraft, Document

# ── Helpers ──────────────────────────────────────────────────────


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
    # Create new draft
    draft = ApplicationDraft.objects.create()
    request.session["draft_token"] = str(draft.token)
    return draft


def _get_step_context(draft, current_step):
    """Build the progress bar context for the form template."""
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "own_it_now")
    purchase_type = form_data.get("purchase_type", "cash")

    steps = _get_active_steps(program_type, purchase_type)
    total_steps = len(steps)

    if current_step in steps:
        position = steps.index(current_step) + 1
    else:
        position = current_step

    return {
        "current_step": position,
        "total_steps": total_steps,
        "step_range": range(1, total_steps + 1),
        "active_steps": steps,
    }


def _get_active_steps(program_type, purchase_type):
    """
    Return list of active step numbers based on program/purchase type.

    Core steps: 1, 2, 3, 4, 5, 8
    Conditional: 6 (rehab), 7 (land contract)
    """
    steps = [1, 2, 3, 4, 5]
    if program_type == "ready_for_rehab":
        steps.append(6)
    if purchase_type == "land_contract":
        steps.append(7)
    steps.append(8)
    return steps


def _get_next_step(draft, current_step):
    """Determine the next step number, skipping inactive steps."""
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "own_it_now")
    purchase_type = form_data.get("purchase_type", "cash")
    steps = _get_active_steps(program_type, purchase_type)

    if current_step in steps:
        idx = steps.index(current_step)
        if idx + 1 < len(steps):
            return steps[idx + 1]
    return None


def _get_prev_step(draft, current_step):
    """Determine the previous step number, skipping inactive steps."""
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "own_it_now")
    purchase_type = form_data.get("purchase_type", "cash")
    steps = _get_active_steps(program_type, purchase_type)

    if current_step in steps:
        idx = steps.index(current_step)
        if idx > 0:
            return steps[idx - 1]
    return None


STEP_TITLES = {
    1: "Your Information",
    2: "Property Information",
    3: "Offer Details",
    4: "Eligibility",
    5: "Documents",
    6: "Rehab Plan",
    7: "Land Contract Details",
    8: "Review & Submit",
}


# ── Step Views ───────────────────────────────────────────────────


def apply_start(request):
    """Step 1: Applicant Identity — creates draft on first POST."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = Step1IdentityForm(request.POST)
        if form.is_valid():
            form_data.update(form.cleaned_data)
            draft.form_data = form_data
            draft.email = form.cleaned_data["email"]
            draft.current_step = 2
            draft.save()
            return redirect("applications:step2")
    else:
        form = Step1IdentityForm(initial=form_data)

    ctx = _get_step_context(draft, 1)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[1],
            "has_file_upload": False,
        }
    )
    return render(request, "apply/step1_identity.html", ctx)


def step2_property(request):
    """Step 2: Property Information."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = Step2PropertyForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if cleaned.get("open_house_date"):
                cleaned["open_house_date"] = cleaned["open_house_date"].isoformat()
            form_data.update(cleaned)
            draft.form_data = form_data
            draft.current_step = 3
            draft.save()
            return redirect("applications:step3")
    else:
        form = Step2PropertyForm(initial=form_data)

    ctx = _get_step_context(draft, 2)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[2],
            "has_file_upload": False,
            "prev_url": "/apply/",
        }
    )
    return render(request, "apply/step2_property.html", ctx)


def step3_offer(request):
    """Step 3: Offer Details."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = Step3OfferForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            cleaned["offer_amount"] = str(cleaned["offer_amount"])
            form_data.update(cleaned)
            draft.form_data = form_data
            draft.current_step = 4
            draft.save()
            return redirect("applications:step4")
    else:
        form = Step3OfferForm(initial=form_data)

    ctx = _get_step_context(draft, 3)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[3],
            "has_file_upload": False,
            "prev_url": "/apply/step2/",
        }
    )
    return render(request, "apply/step3_offer.html", ctx)


def step4_eligibility(request):
    """Step 4: Eligibility gate — hard block if disqualified."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = Step4EligibilityForm(request.POST)
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

            draft.current_step = 5
            draft.save()
            return redirect("applications:step5")
    else:
        initial = {}
        if "has_delinquent_taxes" in form_data:
            initial["has_delinquent_taxes"] = "yes" if form_data["has_delinquent_taxes"] else "no"
        if "has_tax_foreclosure" in form_data:
            initial["has_tax_foreclosure"] = "yes" if form_data["has_tax_foreclosure"] else "no"
        form = Step4EligibilityForm(initial=initial)

    ctx = _get_step_context(draft, 4)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[4],
            "has_file_upload": False,
            "prev_url": "/apply/step3/",
        }
    )
    return render(request, "apply/step4_eligibility.html", ctx)


def step5_documents(request):
    """Step 5: Document uploads — conditional on purchase_type."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}
    purchase_type = form_data.get("purchase_type", "cash")

    required_docs = ["photo_id"]
    if purchase_type == "cash":
        required_docs.append("proof_of_funds")
    elif purchase_type == "land_contract":
        required_docs.extend(["pay_stub_1", "pay_stub_2", "bank_statement"])
    elif purchase_type in ("conventional", "fha_va"):
        required_docs.append("preapproval")

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

        if not all_uploaded:
            ctx = _get_step_context(draft, 5)
            ctx.update(
                {
                    "step_title": STEP_TITLES[5],
                    "has_file_upload": True,
                    "required_docs": required_docs,
                    "uploaded": uploaded,
                    "error": "Please upload all required documents.",
                    "prev_url": "/apply/step4/",
                    "doc_labels": dict(Document.DocType.choices),
                }
            )
            return render(request, "apply/step5_documents.html", ctx)

        next_step = _get_next_step(draft, 5)
        draft.current_step = next_step
        draft.save()
        return redirect(f"/apply/step{next_step}/")

    uploaded = form_data.get("uploads", {})
    ctx = _get_step_context(draft, 5)
    ctx.update(
        {
            "step_title": STEP_TITLES[5],
            "has_file_upload": True,
            "required_docs": required_docs,
            "uploaded": uploaded,
            "prev_url": "/apply/step4/",
            "doc_labels": dict(Document.DocType.choices),
        }
    )
    return render(request, "apply/step5_documents.html", ctx)


def step6_rehab(request):
    """Step 6: Rehab Plan — only for Ready for Rehab program."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if form_data.get("program_type") != "ready_for_rehab":
        next_step = _get_next_step(draft, 6)
        if next_step:
            return redirect(f"/apply/step{next_step}/")
        return redirect("applications:step8")

    if request.method == "POST":
        form = Step6RehabForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            cleaned["rehab_budget"] = str(cleaned["rehab_budget"])
            form_data.update(cleaned)
            draft.form_data = form_data
            next_step = _get_next_step(draft, 6)
            draft.current_step = next_step
            draft.save()
            return redirect(f"/apply/step{next_step}/")
    else:
        form = Step6RehabForm(initial=form_data)

    ctx = _get_step_context(draft, 6)
    prev = _get_prev_step(draft, 6)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[6],
            "has_file_upload": False,
            "prev_url": f"/apply/step{prev}/" if prev else "/apply/step5/",
        }
    )
    return render(request, "apply/step6_rehab.html", ctx)


def step7_land_contract(request):
    """Step 7: Land Contract Details — only for land contract purchases."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if form_data.get("purchase_type") != "land_contract":
        return redirect("applications:step8")

    if request.method == "POST":
        form = Step7LandContractForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            cleaned["lc_interest_rate"] = str(cleaned["lc_interest_rate"])
            form_data.update(cleaned)
            draft.form_data = form_data
            draft.current_step = 8
            draft.save()
            return redirect("applications:step8")
    else:
        form = Step7LandContractForm(initial=form_data)

    ctx = _get_step_context(draft, 7)
    prev = _get_prev_step(draft, 7)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[7],
            "has_file_upload": False,
            "prev_url": f"/apply/step{prev}/" if prev else "/apply/step5/",
        }
    )
    return render(request, "apply/step7_land_contract.html", ctx)


def step8_acknowledgments(request):
    """Step 8: Acknowledgments + submit."""
    draft = _get_draft(request)
    form_data = draft.form_data or {}

    if request.method == "POST":
        form = Step8AcknowledgmentsForm(request.POST)
        if form.is_valid():
            form_data.update(form.cleaned_data)
            draft.form_data = form_data
            draft.save()
            return _submit_application(request, draft)
    else:
        form = Step8AcknowledgmentsForm(initial=form_data)

    ctx = _get_step_context(draft, 8)
    prev = _get_prev_step(draft, 8)
    ctx.update(
        {
            "form": form,
            "step_title": STEP_TITLES[8],
            "has_file_upload": False,
            "form_data": form_data,
            "prev_url": f"/apply/step{prev}/" if prev else "/apply/step5/",
        }
    )
    return render(request, "apply/step8_acknowledgments.html", ctx)


# ── Submission ───────────────────────────────────────────────────


def _submit_application(request, draft):
    """Convert draft into a real Application with Documents and send emails."""
    data = draft.form_data

    app = Application(
        reference_number=Application.generate_reference_number(),
        status=Application.Status.SUBMITTED,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        preferred_contact=data.get("preferred_contact", "email"),
        street_address=data.get("street_address", ""),
        city=data.get("city", ""),
        state=data.get("state", "MI"),
        zip_code=data.get("zip_code", ""),
        property_address=data.get("property_address", ""),
        parcel_id=data.get("parcel_id", ""),
        program_type=data.get("program_type", "own_it_now"),
        attended_open_house=data.get("attended_open_house", False),
        offer_amount=Decimal(data.get("offer_amount", "0")),
        purchase_type=data.get("purchase_type", "cash"),
        intended_use=data.get("intended_use", "primary_residence"),
        has_delinquent_taxes=data.get("has_delinquent_taxes", False),
        has_tax_foreclosure=data.get("has_tax_foreclosure", False),
        rehab_scope=data.get("rehab_scope", ""),
        rehab_budget=Decimal(data["rehab_budget"]) if data.get("rehab_budget") else None,
        rehab_timeline=data.get("rehab_timeline", ""),
        contractor_name=data.get("contractor_name", ""),
        contractor_phone=data.get("contractor_phone", ""),
        lc_provider_name=data.get("lc_provider_name", ""),
        lc_provider_phone=data.get("lc_provider_phone", ""),
        lc_term_months=data.get("lc_term_months"),
        lc_interest_rate=(
            Decimal(data["lc_interest_rate"]) if data.get("lc_interest_rate") else None
        ),
        ack_info_accurate=data.get("ack_info_accurate", False),
        ack_terms_conditions=data.get("ack_terms_conditions", False),
        ack_inspection_waiver=data.get("ack_inspection_waiver", False),
    )

    if data.get("open_house_date"):
        from datetime import date

        app.open_house_date = date.fromisoformat(data["open_house_date"])

    app.save()

    # Move uploaded files from drafts/ to applications/
    uploads = data.get("uploads", {})
    for doc_type, info in uploads.items():
        if info.get("path") and os.path.exists(info["path"]):
            dest_dir = os.path.join(
                settings.MEDIA_ROOT,
                "applications",
                str(timezone.now().year),
                f"{timezone.now().month:02d}",
            )
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{app.reference_number}_{info['filename']}")
            shutil.move(info["path"], dest_path)

            relative_path = os.path.relpath(dest_path, settings.MEDIA_ROOT)
            Document.objects.create(
                application=app,
                doc_type=doc_type,
                file=relative_path,
                original_filename=info["filename"],
            )

    # Clean up draft directory
    draft_dir = os.path.join(settings.MEDIA_ROOT, "drafts", str(draft.token))
    if os.path.exists(draft_dir):
        shutil.rmtree(draft_dir)

    # Email to buyer
    send_mail(
        subject=f"GCLBA Application Received — {app.reference_number}",
        message=(
            f"Dear {app.first_name},\n\n"
            f"Your application {app.reference_number} has been received.\n"
            f"Property: {app.property_address}\n"
            f"Offer: ${app.offer_amount:,.2f}\n\n"
            "Our team will review your application and contact you within "
            "5-7 business days.\n\n"
            "Genesee County Land Bank Authority\n"
            "(810) 257-3088\n"
            "offers@thelandbank.org"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[app.email],
        fail_silently=True,
    )

    # Email to staff
    send_mail(
        subject=f"New Application: {app.reference_number} — {app.full_name}",
        message=(
            f"New application submitted:\n\n"
            f"Reference: {app.reference_number}\n"
            f"Applicant: {app.full_name}\n"
            f"Email: {app.email}\n"
            f"Phone: {app.phone}\n"
            f"Property: {app.property_address}\n"
            f"Offer: ${app.offer_amount:,.2f}\n"
            f"Purchase Type: {app.get_purchase_type_display()}\n"
            f"Program: {app.get_program_type_display()}\n\n"
            f"Review in admin: /admin/applications/application/{app.pk}/change/"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.STAFF_NOTIFICATION_EMAIL],
        fail_silently=True,
    )

    # Clear session
    if "draft_token" in request.session:
        del request.session["draft_token"]

    draft.delete()

    return render(request, "apply/confirmation.html", {"application": app})


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

    send_mail(
        subject="Continue Your GCLBA Application",
        message=(
            f"You can continue your application at any time using this link:\n\n"
            f"{resume_url}\n\n"
            f"This link expires on {draft.expires_at.strftime('%B %d, %Y')}.\n\n"
            "Genesee County Land Bank Authority\n"
            "(810) 257-3088"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[draft.email],
        fail_silently=True,
    )

    return HttpResponse(
        '<span class="text-gclba-600">'
        "&#10003; Progress saved! Check your email for a resume link.</span>"
    )


def resume_draft(request, token):
    """Resume a draft from a magic link."""
    draft = get_object_or_404(ApplicationDraft, token=token)

    if draft.is_expired:
        return render(request, "apply/link_expired.html")

    request.session["draft_token"] = str(draft.token)

    step = draft.current_step
    if step == 1:
        return redirect("applications:step1")
    return redirect(f"/apply/step{step}/")
