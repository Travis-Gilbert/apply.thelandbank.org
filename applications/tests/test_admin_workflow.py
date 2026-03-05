"""
Tests for admin workflow: review queue, admin API endpoints, bulk actions.
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from applications.models import Application, Document, StatusLog

User = get_user_model()

TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(
    STORAGES=TEST_STORAGES,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ReviewQueueTests(TestCase):
    """Tests for the /admin/review/ workflow."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="reviewer",
            password="testpass123",
            is_staff=True,
            first_name="Alex",
            last_name="Riley",
        )
        self.client.login(username="reviewer", password="testpass123")

        self.app = Application.objects.create(
            reference_number="GCLBA-2026-0099",
            status=Application.Status.RECEIVED,
            first_name="Test",
            last_name="Buyer",
            email="buyer@example.com",
            phone="810-555-0000",
            mailing_address="123 Test St",
            city="Flint",
            state="MI",
            zip_code="48502",
            property_address="456 Example Ave",
            program_type=Application.ProgramType.FEATURED_HOMES,
            purchase_type=Application.PurchaseType.CASH,
        )

    def test_review_queue_redirects_to_first_app(self):
        response = self.client.get("/admin/review/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.app.pk), response.url)

    def test_review_queue_empty_state(self):
        self.app.status = Application.Status.APPROVED
        self.app.save()
        response = self.client.get("/admin/review/")
        self.assertEqual(response.status_code, 200)

    def test_review_update_status_creates_log(self):
        response = self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "under_review", "note": "Starting review"},
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "under_review")
        log = StatusLog.objects.filter(
            application=self.app,
            from_status="received",
            to_status="under_review",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.from_status, "received")
        self.assertEqual(log.to_status, "under_review")

    def test_review_update_auto_claims_unassigned(self):
        self.assertIsNone(self.app.assigned_to)
        self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "under_review", "note": ""},
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.assigned_to, self.staff)

    def test_review_update_rejects_invalid_transition(self):
        response = self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "approved", "note": ""},
        )
        self.assertEqual(response.status_code, 422)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "received")

    def test_review_update_requires_note_for_needs_more_info(self):
        # First move to under_review
        self.app.status = Application.Status.UNDER_REVIEW
        self.app.save()

        response = self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "needs_more_info", "note": ""},
        )
        self.assertEqual(response.status_code, 422)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "under_review")

    def test_review_update_sends_buyer_email(self):
        # Move to under_review first
        self.app.status = Application.Status.UNDER_REVIEW
        self.app.assigned_to = self.staff
        self.app.save()

        self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "needs_more_info", "note": "Please upload proof of funds."},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("More Information Needed", mail.outbox[0].subject)

    def test_review_update_no_email_for_under_review(self):
        self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "under_review", "note": ""},
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_review_update_does_not_loop_back_to_same_app(self):
        """After updating the only queued app, redirect to empty state, not the same app."""
        response = self.client.post(
            f"/admin/review/{self.app.pk}/update/",
            {"status": "under_review", "note": ""},
            follow=True,
        )
        # Should land on the empty queue page, not loop back to this app
        self.assertNotIn(
            f"/admin/review/{self.app.pk}/",
            response.redirect_chain[-1][0] if response.redirect_chain else "",
        )
        self.assertEqual(response.status_code, 200)


@override_settings(STORAGES=TEST_STORAGES)
class AdminAPITests(TestCase):
    """Tests for /admin/api/ endpoints."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffer",
            password="testpass123",
            is_staff=True,
            first_name="Staff",
            last_name="Member",
        )
        self.client.login(username="staffer", password="testpass123")

        self.app = Application.objects.create(
            reference_number="GCLBA-2026-0100",
            status=Application.Status.RECEIVED,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="810-555-1111",
            mailing_address="789 Oak St",
            city="Flint",
            state="MI",
            zip_code="48502",
            property_address="321 Elm Ave",
            program_type=Application.ProgramType.READY_FOR_REHAB,
            purchase_type=Application.PurchaseType.CASH,
        )

    def test_assign_to_me_sets_reviewer(self):
        response = self.client.post(f"/admin/api/assign/{self.app.pk}/")
        self.assertEqual(response.status_code, 200)
        self.app.refresh_from_db()
        self.assertEqual(self.app.assigned_to, self.staff)

    def test_assign_to_me_creates_audit_log(self):
        self.client.post(f"/admin/api/assign/{self.app.pk}/")
        log = StatusLog.objects.filter(application=self.app).first()
        self.assertIsNotNone(log)
        self.assertIn("Claimed for review", log.notes)

    def test_pending_count_returns_json(self):
        response = self.client.get("/admin/api/pending/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)

    def test_doc_review_saves_status(self):
        doc = Document.objects.create(
            application=self.app,
            doc_type="photo_id",
            file=SimpleUploadedFile("id.pdf", b"%PDF-test", content_type="application/pdf"),
            original_filename="id.pdf",
        )
        response = self.client.post(
            f"/admin/api/doc-review/{self.app.pk}/",
            data='{"doc_id": "' + str(doc.pk) + '", "status": "ok"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.app.refresh_from_db()
        self.assertEqual(self.app.document_review.get(str(doc.pk)), "ok")

    def test_doc_review_rejects_invalid_doc(self):
        response = self.client.post(
            f"/admin/api/doc-review/{self.app.pk}/",
            data='{"doc_id": "99999", "status": "ok"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_document_thumbnail_returns_image_for_uploaded_image(self):
        image_data = BytesIO()
        Image.new("RGB", (20, 20), color="red").save(image_data, format="PNG")
        image_data.seek(0)

        doc = Document.objects.create(
            application=self.app,
            doc_type="photo_id",
            file=SimpleUploadedFile("id.png", image_data.read(), content_type="image/png"),
            original_filename="id.png",
        )
        response = self.client.get(
            reverse("applications:document_thumbnail", args=[doc.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("image/"))

    def test_document_thumbnail_pdf_returns_preview_or_placeholder(self):
        doc = Document.objects.create(
            application=self.app,
            doc_type="photo_id",
            file=SimpleUploadedFile("id.pdf", b"%PDF-test", content_type="application/pdf"),
            original_filename="id.pdf",
        )
        response = self.client.get(
            reverse("applications:document_thumbnail", args=[doc.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            response["Content-Type"],
            {"image/png", "image/svg+xml"},
        )


class TransitionEnforcementTests(TestCase):
    """Tests that the state machine is enforced in all pathways."""

    def setUp(self):
        self.app = Application.objects.create(
            reference_number="GCLBA-2026-0101",
            status=Application.Status.RECEIVED,
            first_name="Test",
            last_name="Transitions",
            email="test@example.com",
            phone="810-555-2222",
            mailing_address="100 Main St",
            city="Flint",
            state="MI",
            zip_code="48502",
            property_address="200 Oak St",
            program_type=Application.ProgramType.FEATURED_HOMES,
            purchase_type=Application.PurchaseType.CASH,
        )

    def test_allowed_transitions_map_is_complete(self):
        """Every status value has an entry in ALLOWED_TRANSITIONS."""
        for status_value, _ in Application.Status.choices:
            self.assertIn(
                status_value,
                Application.ALLOWED_TRANSITIONS,
                f"Status '{status_value}' missing from ALLOWED_TRANSITIONS",
            )

    def test_approved_is_terminal(self):
        self.assertEqual(Application.ALLOWED_TRANSITIONS["approved"], set())

    def test_declined_allows_reopen(self):
        self.assertIn("under_review", Application.ALLOWED_TRANSITIONS["declined"])
