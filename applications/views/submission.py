"""
Application submission — converts an ApplicationDraft into a real
Application with Documents, sends confirmation emails.
"""

import os
import shutil
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.utils import timezone

from ..models import Application, Document


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

    app.save()

    # Move uploaded files from drafts/ to applications/
    _move_documents(draft, app, data)

    # Emails
    _send_buyer_confirmation(app)
    _send_staff_notification(app)

    # Clean up
    _cleanup_draft(request, draft)

    return render(request, "apply/confirmation.html", {"application": app})


def _move_documents(draft, app, data):
    """Move uploaded files from drafts/ to applications/ and create Document records."""
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


def _send_buyer_confirmation(app):
    """Send submission confirmation email to the buyer."""
    # Build program-specific summary
    if app.program_type == Application.ProgramType.VIP_SPOTLIGHT:
        offer_line = "Program: VIP Spotlight (proposal-based)"
    else:
        offer_line = f"Offer: ${app.offer_amount:,.2f}" if app.offer_amount else ""

    send_mail(
        subject=f"GCLBA Application Received — {app.reference_number}",
        message=(
            f"Dear {app.first_name},\n\n"
            f"Your application {app.reference_number} has been received.\n"
            f"Property: {app.property_address}\n"
            f"Program: {app.get_program_type_display()}\n"
            f"{offer_line}\n\n"
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


def _send_staff_notification(app):
    """Send new application alert to staff."""
    send_mail(
        subject=f"New Application: {app.reference_number} — {app.full_name}",
        message=(
            f"New application submitted:\n\n"
            f"Reference: {app.reference_number}\n"
            f"Applicant: {app.full_name}\n"
            f"Email: {app.email}\n"
            f"Phone: {app.phone}\n"
            f"Property: {app.property_address}\n"
            f"Program: {app.get_program_type_display()}\n"
            f"Purchase Type: {app.get_purchase_type_display()}\n"
            f"Offer: ${app.offer_amount:,.2f}\n\n"
            f"Review in admin: /admin/applications/application/{app.pk}/change/"
        ) if app.offer_amount else (
            f"New application submitted:\n\n"
            f"Reference: {app.reference_number}\n"
            f"Applicant: {app.full_name}\n"
            f"Email: {app.email}\n"
            f"Phone: {app.phone}\n"
            f"Property: {app.property_address}\n"
            f"Program: {app.get_program_type_display()}\n\n"
            f"Review in admin: /admin/applications/application/{app.pk}/change/"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.STAFF_NOTIFICATION_EMAIL],
        fail_silently=True,
    )


def _cleanup_draft(request, draft):
    """Remove draft and clear session."""
    if "draft_token" in request.session:
        del request.session["draft_token"]
    draft.delete()
