"""
Application submission — converts an ApplicationDraft into a real
Application with Documents, sends confirmation emails.
"""

import logging
import os
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ..models import Application, Document

logger = logging.getLogger(__name__)


def submit_application(request, draft):
    """
    Convert a completed draft into a submitted Application.

    1. Hydrate flat Application fields from draft.form_data
    2. Move uploaded files from drafts/ to applications/
    3. Send confirmation email to buyer
    4. Send notification email to staff
    5. Clean up draft
    """
    data = draft.form_data
    program_type = data.get("program_type", "featured_homes")

    app = Application(
        reference_number=Application.generate_reference_number(),
        status=Application.Status.RECEIVED,
        # Identity
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        preferred_contact=data.get("preferred_contact", "email"),
        mailing_address=data.get("mailing_address", ""),
        city=data.get("city", ""),
        state=data.get("state", "MI"),
        zip_code=data.get("zip_code", ""),
        purchasing_entity_name=data.get("purchasing_entity_name", ""),
        contact_name_different=data.get("contact_name_different", ""),
        # Property
        property_address=data.get("property_address", ""),
        parcel_id=data.get("parcel_id", ""),
        program_type=program_type,
        attended_open_house=data.get("attended_open_house", False),
        # Eligibility
        has_delinquent_taxes=data.get("has_delinquent_taxes", False),
        has_tax_foreclosure=data.get("has_tax_foreclosure", False),
        # Offer (FH + R4R)
        purchase_type=data.get("purchase_type", "cash"),
        # Acknowledgments (all programs)
        ack_sold_as_is=data.get("ack_sold_as_is", False),
        ack_quit_claim_deed=data.get("ack_quit_claim_deed", False),
        ack_no_title_insurance=data.get("ack_no_title_insurance", False),
        ack_highest_not_guaranteed=data.get("ack_highest_not_guaranteed", False),
        ack_info_accurate=data.get("ack_info_accurate", False),
        ack_tax_capture=data.get("ack_tax_capture", False),
        ack_reconveyance_deed=data.get("ack_reconveyance_deed", False),
        ack_no_transfer=data.get("ack_no_transfer", False),
    )

    # Offer amount (FH + R4R only, VIP states price in proposal narrative)
    if data.get("offer_amount"):
        app.offer_amount = Decimal(data["offer_amount"])

    # Down payment (FH land contract only)
    if data.get("down_payment_amount"):
        app.down_payment_amount = Decimal(data["down_payment_amount"])
    app.is_self_employed = data.get("is_self_employed", False)

    # Open house date
    if data.get("open_house_date"):
        app.open_house_date = date.fromisoformat(data["open_house_date"])

    # Intended use + sub-question (FH + R4R)
    app.intended_use = data.get("intended_use", "")
    app.first_home_or_moving = data.get("first_home_or_moving", "")

    # Renovation narrative (FH + R4R)
    app.renovation_description = data.get("renovation_description", "")
    app.renovation_who = data.get("renovation_who", "")
    app.renovation_when = data.get("renovation_when", "")
    app.renovation_funding = data.get("renovation_funding", "")

    # R4R line-item costs
    if program_type == "ready_for_rehab":
        for field_name in Application.INTERIOR_RENO_FIELDS + Application.EXTERIOR_RENO_FIELDS:
            val = data.get(field_name)
            if val is not None:
                setattr(app, field_name, Decimal(str(val)))
        # Stored subtotals/total (calculated by form + view)
        for total_field in ("reno_interior_subtotal", "reno_exterior_subtotal", "reno_total"):
            val = data.get(total_field)
            if val is not None:
                setattr(app, total_field, Decimal(str(val)))

    # R4R prior purchase
    app.has_prior_gclba_purchase = data.get("has_prior_gclba_purchase", False)

    # Homebuyer education (FH land contract only)
    app.homebuyer_ed_completed = data.get("homebuyer_ed_completed", False)
    app.homebuyer_ed_agency = data.get("homebuyer_ed_agency", "")
    app.homebuyer_ed_other = data.get("homebuyer_ed_other", "")

    # VIP proposal fields
    if program_type == "vip_spotlight":
        app.vip_q1_who_and_why = data.get("vip_q1_who_and_why", "")
        app.vip_q2_prior_purchases = data.get("vip_q2_prior_purchases")
        app.vip_q2_prior_detail = data.get("vip_q2_prior_detail", "")
        app.vip_q3_renovation_costs_timeline = data.get("vip_q3_renovation_costs_timeline", "")
        app.vip_q4_financing = data.get("vip_q4_financing", "")
        app.vip_q5_has_experience = data.get("vip_q5_has_experience")
        app.vip_q5_experience_detail = data.get("vip_q5_experience_detail", "")
        app.vip_q6_completion_plan = data.get("vip_q6_completion_plan", "")
        app.vip_q6_completion_detail = data.get("vip_q6_completion_detail", "")
        app.vip_q7_contractor_info = data.get("vip_q7_contractor_info", "")
        app.vip_q8_additional_info = data.get("vip_q8_additional_info", "")

    try:
        with transaction.atomic():
            app.save()

            # Move uploaded files from drafts/ to applications/
            _move_documents(draft, app, data)

            # Mark draft as submitted inside the transaction
            draft.submitted = True
            draft.submitted_at = timezone.now()
            draft.save()
    except Exception:
        logger.exception("Submission failed for draft %s", draft.token)
        return render(request, "apply/submission_error.html", {
            "email": draft.email,
        })

    # Emails happen outside the transaction — non-critical side effects
    _send_buyer_confirmation(app)
    _send_staff_notification(app)

    # Clean up session (but keep draft record since it's marked submitted)
    if "draft_token" in request.session:
        del request.session["draft_token"]

    # Store reference number in session so confirmation page can verify access
    request.session["confirmed_ref"] = app.reference_number

    # HX-Redirect tells HTMX to do a full-page redirect instead of a partial swap.
    # This prevents the old accordion sections from bleeding through on the confirmation page.
    confirmation_url = reverse("applications:confirmation", args=[app.reference_number])
    response = HttpResponse(status=200)
    response["HX-Redirect"] = confirmation_url
    return response


def _move_documents(draft, app, data):
    """
    Move uploaded files from drafts/ to applications/ and create Document records.

    Uses Django's default_storage API so this works transparently with both
    local filesystem (development) and S3/B2 (production).
    """
    uploads = data.get("uploads", {})
    now = timezone.now()
    dest_prefix = f"applications/{now.year}/{now.month:02d}"

    for doc_type, info in uploads.items():
        source_path = info.get("path", "")
        if not source_path or not default_storage.exists(source_path):
            continue

        # Sanitize the original filename for the destination path
        safe_filename = "".join(
            c for c in info["filename"] if c.isalnum() or c in ".-_"
        ) or "upload"
        dest_path = f"{dest_prefix}/{app.reference_number}_{safe_filename}"

        # Read from source, save to destination via storage API
        with default_storage.open(source_path, "rb") as source_file:
            saved_path = default_storage.save(dest_path, source_file)

        # Remove the draft copy
        default_storage.delete(source_path)

        Document.objects.create(
            application=app,
            doc_type=doc_type,
            file=saved_path,
            original_filename=info["filename"],
        )

    # Clean up empty draft directory (local filesystem only)
    draft_dir = os.path.join(settings.MEDIA_ROOT, "drafts", str(draft.token))
    if os.path.isdir(draft_dir):
        try:
            os.rmdir(draft_dir)  # Only removes if empty
        except OSError:
            pass  # Directory not empty or doesn't exist — fine


def _send_buyer_confirmation(app):
    """Send submission confirmation email to the buyer."""
    if app.program_type == Application.ProgramType.VIP_SPOTLIGHT:
        offer_line = ""
    else:
        offer_line = f"Offer: ${app.offer_amount:,.2f}" if app.offer_amount else ""

    context = {
        "application": app,
        "offer_line": offer_line,
        "contact_email": settings.STAFF_NOTIFICATION_EMAIL,
        "contact_phone": "(810) 257-3088",
    }

    try:
        send_mail(
            subject=f"GCLBA Application Received — {app.reference_number}",
            message=render_to_string("emails/submission_confirmation.txt", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[app.email],
            html_message=render_to_string("emails/submission_confirmation.html", context),
        )
    except Exception:
        logger.exception("Failed to send buyer confirmation for %s", app.reference_number)


def _send_staff_notification(app):
    """Send new application alert to staff."""
    context = {
        "application": app,
        "admin_url": f"/admin/applications/application/{app.pk}/change/",
    }

    try:
        send_mail(
            subject=f"New Application: {app.reference_number} — {app.full_name}",
            message=render_to_string("emails/staff_notification.txt", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.STAFF_NOTIFICATION_EMAIL],
            html_message=render_to_string("emails/staff_notification.html", context),
        )
    except Exception:
        logger.exception("Failed to send staff notification for %s", app.reference_number)


def confirmation_page(request, ref):
    """
    Render the post-submission confirmation page.

    Only accessible if the session contains the matching reference number
    (set during submit_application). This prevents random URL guessing.
    """
    if request.session.get("confirmed_ref") != ref:
        from django.shortcuts import redirect
        return redirect("applications:apply_page")

    app = get_object_or_404(Application, reference_number=ref)
    return render(request, "apply/confirmation.html", {"application": app})

