"""
Helpers for status-transition requirements and buyer notification emails.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Application

logger = logging.getLogger(__name__)


NOTE_REQUIRED_STATUSES = {
    Application.Status.NEEDS_MORE_INFO,
    Application.Status.DECLINED,
}

BUYER_EMAIL_STATUSES = {
    Application.Status.NEEDS_MORE_INFO,
    Application.Status.APPROVED,
    Application.Status.DECLINED,
}

STATUS_SUBJECTS = {
    Application.Status.NEEDS_MORE_INFO: "GCLBA Application Update — More Information Needed",
    Application.Status.APPROVED: "GCLBA Application Update — Approved",
    Application.Status.DECLINED: "GCLBA Application Update",
}


def requires_transition_note(status):
    """Return True when a status transition must include a staff note."""
    return status in NOTE_REQUIRED_STATUSES


def send_buyer_status_email(application, old_status="", note=""):
    """
    Send buyer status notification email when status reaches a buyer-facing state.

    Returns one of: sent, not_applicable, failed.
    """
    if application.status not in BUYER_EMAIL_STATUSES or not application.email:
        return "not_applicable"

    status_key = application.status
    status_labels = dict(Application.Status.choices)
    context = {
        "application": application,
        "note": note.strip(),
        "old_status_label": status_labels.get(old_status, old_status or "Received"),
        "new_status_label": application.get_status_display(),
        "contact_email": settings.STAFF_NOTIFICATION_EMAIL,
        "contact_phone": "(810) 257-3088",
    }

    subject = STATUS_SUBJECTS.get(
        status_key,
        f"GCLBA Application Update — {application.get_status_display()}",
    )
    txt_template = f"emails/status_change_{status_key}.txt"
    html_template = f"emails/status_change_{status_key}.html"

    try:
        text_body = render_to_string(txt_template, context)
        html_body = render_to_string(html_template, context)
        send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.email],
            html_message=html_body,
        )
    except Exception:
        logger.exception(
            "Failed to send status-change email for %s (%s)",
            application.reference_number,
            application.status,
        )
        return "failed"

    return "sent"
