from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings

from .admin import ApplicationAdminForm
from .models import Application, ApplicationDraft
from .status_notifications import requires_transition_note, send_buyer_status_email

TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


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


@override_settings(STORAGES=TEST_STORAGES)
class DraftExperienceTests(TestCase):
    def _set_draft_session(self, draft):
        session = self.client.session
        session["draft_token"] = str(draft.token)
        session.save()

    def test_contact_validation_persists_draft_email(self):
        draft = ApplicationDraft.objects.create(
            form_data={
                "program_type": Application.ProgramType.FEATURED_HOMES,
                "purchase_type": Application.PurchaseType.CASH,
            },
        )
        self._set_draft_session(draft)

        response = self.client.post(
            "/apply/section/contact/validate/",
            {
                "first_name": "Alex",
                "last_name": "Buyer",
                "email": "alex@example.com",
                "phone": "810-555-1234",
                "preferred_contact": "email",
                "mailing_address": "123 Main St",
                "city": "Flint",
                "state": "MI",
                "zip_code": "48502",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.email, "alex@example.com")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_save_progress_uses_posted_email_before_contact_step_submit(self):
        self.client.get("/apply/")
        response = self.client.post(
            "/apply/save/",
            {
                "email": "resume@example.com",
                "first_name": "Riley",
                "property_address": "123 Main St",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Progress saved", response.content.decode())
        draft = ApplicationDraft.objects.latest("created_at")
        self.assertEqual(draft.email, "resume@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["resume@example.com"])


@override_settings(STORAGES=TEST_STORAGES)
class DocumentUploadBehaviorTests(TestCase):
    def _set_draft_session(self, draft):
        session = self.client.session
        session["draft_token"] = str(draft.token)
        session.save()

    def _fake_pdf(self, name):
        return SimpleUploadedFile(name, b"%PDF-1.4 test file", content_type="application/pdf")

    def test_vip_documents_accept_multiple_files_and_remove_flag(self):
        draft = ApplicationDraft.objects.create(
            form_data={
                "program_type": Application.ProgramType.VIP_SPOTLIGHT,
                "purchase_type": Application.PurchaseType.CASH,
                "uploads": {},
            },
            program_type=Application.ProgramType.VIP_SPOTLIGHT,
        )
        self._set_draft_session(draft)

        response = self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": self._fake_pdf("photo-id.pdf"),
                "proof_of_funds": self._fake_pdf("funds.pdf"),
                "vip_portfolio_photo": [
                    self._fake_pdf("portfolio-1.pdf"),
                    self._fake_pdf("portfolio-2.pdf"),
                ],
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        draft.refresh_from_db()
        uploads = draft.form_data.get("uploads", {})
        self.assertIn("vip_portfolio_photo", uploads)
        self.assertIsInstance(uploads["vip_portfolio_photo"], list)
        self.assertEqual(len(uploads["vip_portfolio_photo"]), 2)

        response = self.client.post(
            "/apply/section/documents/validate/",
            {
                "remove_vip_portfolio_photo": "1",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        draft.refresh_from_db()
        uploads = draft.form_data.get("uploads", {})
        self.assertNotIn("vip_portfolio_photo", uploads)
