from django.core import mail
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings

from .admin import ApplicationAdminForm
from .models import Application
from .status_notifications import requires_transition_note, send_buyer_status_email


class StatusNotificationTests(TestCase):
    def _create_application(self, status=Application.Status.RECEIVED, ref="GCLBA-2026-0001"):
        return Application.objects.create(
            reference_number=ref,
            status=status,
            first_name="Taylor",
            last_name="Buyer",
            email="buyer@example.com",
            phone="810-555-1212",
            mailing_address="302 E Kearsley St",
            city="Flint",
            state="MI",
            zip_code="48502",
            property_address="123 Example Ave",
            program_type=Application.ProgramType.FEATURED_HOMES,
            purchase_type=Application.PurchaseType.CASH,
        )

    def test_requires_transition_note_only_for_expected_statuses(self):
        self.assertTrue(requires_transition_note(Application.Status.NEEDS_MORE_INFO))
        self.assertTrue(requires_transition_note(Application.Status.DECLINED))
        self.assertFalse(requires_transition_note(Application.Status.UNDER_REVIEW))
        self.assertFalse(requires_transition_note(Application.Status.APPROVED))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_status_email_for_needs_more_info(self):
        app = self._create_application(status=Application.Status.NEEDS_MORE_INFO)
        outcome = send_buyer_status_email(app, old_status=Application.Status.UNDER_REVIEW, note="Upload proof of funds.")

        self.assertEqual(outcome, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("More Information Needed", mail.outbox[0].subject)
        self.assertIn("Upload proof of funds.", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_status_email_not_applicable_for_internal_status(self):
        app = self._create_application(status=Application.Status.UNDER_REVIEW, ref="GCLBA-2026-0002")
        outcome = send_buyer_status_email(app, old_status=Application.Status.RECEIVED, note="")

        self.assertEqual(outcome, "not_applicable")
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_form_requires_note_when_setting_needs_more_info(self):
        app = self._create_application(status=Application.Status.RECEIVED, ref="GCLBA-2026-0003")
        editable_fields = [f.name for f in Application._meta.fields if f.editable and f.name != "id"]
        data = model_to_dict(app, fields=editable_fields)
        data["status"] = Application.Status.NEEDS_MORE_INFO
        data["staff_notes"] = ""

        form = ApplicationAdminForm(data=data, instance=app)
        self.assertFalse(form.is_valid())
        self.assertIn("staff_notes", form.errors)
