"""
End-to-end tests for the accordion application flow.

Tests all three program paths through the full accordion:
  1. Featured Homes (cash)
  2. Featured Homes (land contract)
  3. Ready for Rehab
  4. VIP Spotlight

Each test walks through every section in order:
  program → contact → property → eligibility → [program-specific] → acks/submit
"""

import io

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from applications.models import Application, ApplicationDraft

# Use console email backend so we can inspect mail.outbox
# Use local file storage so we don't need S3
E2E_SETTINGS = {
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "DEFAULT_FILE_STORAGE": "django.core.files.storage.FileSystemStorage",
    "RATELIMIT_ENABLE": False,
}


def _fake_pdf(name="test.pdf"):
    """Create a minimal fake PDF for upload testing."""
    content = b"%PDF-1.4 fake"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _fake_image(name="id.jpg"):
    """Create a minimal fake JPEG for upload testing."""
    from PIL import Image

    image_io = io.BytesIO()
    image = Image.new("RGB", (10, 10), color="white")
    image.save(image_io, format="JPEG")
    image_io.seek(0)
    return SimpleUploadedFile(name, image_io.read(), content_type="image/jpeg")


# ── Shared identity/property/eligibility data ─────────────────────

IDENTITY_DATA = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone": "810-555-1234",
    "mailing_address": "123 Test Street",
    "city": "Flint",
    "state": "MI",
    "zip_code": "48502",
    "preferred_contact": "email",
}

def _property_search_data(program_type):
    return {
        "property_address": "456 Main St, Flint, MI",
        "parcel_id": "41-20-100-001",
        "program_type": program_type,
    }

ELIGIBLE_DATA = {
    "has_delinquent_taxes": "no",
    "has_tax_foreclosure": "no",
}

DISQUALIFIED_DATA = {
    "has_delinquent_taxes": "yes",
    "has_tax_foreclosure": "no",
}


@override_settings(**E2E_SETTINGS)
class FeaturedHomesCashE2ETest(TestCase):
    """Walk a Featured Homes cash application through every accordion section."""

    def test_full_flow(self):
        # ── Step 1: Load apply page ──────────────────────────────
        resp = self.client.get("/apply/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Featured Homes")

        # ── Step 2: Property search + program ────────────────────
        resp = self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("featured_homes"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Contact Information", resp.content)

        # ── Step 3: Contact/Identity ─────────────────────────────
        resp = self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"This field is required", resp.content)
        self.assertIn(b"Property", resp.content)

        # ── Step 4: Eligibility ──────────────────────────────────
        resp = self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        # Should NOT redirect to disqualified
        self.assertNotIn(b"disqualified", resp.content.lower())
        self.assertIn(b"Offer", resp.content)

        # ── Step 5: Offer details (cash) ─────────────────────────
        resp = self.client.post(
            "/apply/section/offer/validate/",
            {
                "offer_amount": "45000.00",
                "purchase_type": "cash",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 6: Documents ────────────────────────────────────
        resp = self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": _fake_image("photo_id.jpg"),
                "proof_of_funds": _fake_pdf("bank_statement.pdf"),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 7: Renovation narrative ─────────────────────────
        resp = self.client.post(
            "/apply/section/renovation/validate/",
            {
                "intended_use": "renovate_move_in",
                "first_home_or_moving": "first_home",
                "renovation_description": "Replace roof, update kitchen and bathrooms",
                "renovation_who": "Licensed contractor",
                "renovation_when": "Within 6 months of purchase",
                "renovation_funding": "Personal savings and home improvement loan",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 8: Acknowledgments & Submit ─────────────────────
        resp = self.client.post(
            "/apply/section/acks/validate/",
            {
                "ack_sold_as_is": "on",
                "ack_quit_claim_deed": "on",
                "ack_no_title_insurance": "on",
                "ack_highest_not_guaranteed": "on",
                "ack_info_accurate": "on",
                "ack_tax_capture": "on",
            },
            HTTP_HX_REQUEST="true",
        )
        # Should redirect to confirmation page after submission
        self.assertIn(resp.status_code, [200, 302])

        # Verify application was created
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertEqual(app.program_type, "featured_homes")
        self.assertEqual(app.purchase_type, "cash")
        self.assertEqual(app.first_name, "Jane")
        self.assertEqual(app.last_name, "Doe")
        self.assertEqual(str(app.offer_amount), "45000.00")
        self.assertTrue(app.reference_number.startswith("GCLBA-"))

        # Verify emails sent (buyer confirmation + staff notification)
        self.assertGreaterEqual(len(mail.outbox), 1)


@override_settings(**E2E_SETTINGS)
class FeaturedHomesLandContractE2ETest(TestCase):
    """Walk a Featured Homes land contract application through every section."""

    def test_full_flow(self):
        # Property search + program
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("featured_homes"),
            HTTP_HX_REQUEST="true",
        )

        # Contact
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )

        # Eligibility
        self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )

        # Offer (land contract with down payment)
        resp = self.client.post(
            "/apply/section/offer/validate/",
            {
                "offer_amount": "50000.00",
                "purchase_type": "land_contract",
                "down_payment_amount": "5000.00",  # 10% of 50k
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # Documents (land contract needs income proof + down payment proof)
        self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": _fake_image("id.jpg"),
                "proof_of_income": _fake_pdf("paystubs.pdf"),
                "proof_of_down_payment": _fake_pdf("savings.pdf"),
            },
            HTTP_HX_REQUEST="true",
        )

        # Renovation narrative
        self.client.post(
            "/apply/section/renovation/validate/",
            {
                "intended_use": "renovate_move_in",
                "first_home_or_moving": "neither",
                "renovation_description": "Full interior renovation",
                "renovation_who": "Self and family",
                "renovation_when": "12 months",
                "renovation_funding": "Savings",
            },
            HTTP_HX_REQUEST="true",
        )

        # Homebuyer education (land contract only)
        self.client.post(
            "/apply/section/homebuyer_ed/validate/",
            {
                "homebuyer_ed_completed": "on",
                "homebuyer_ed_agency": "metro_community_dev",
            },
            HTTP_HX_REQUEST="true",
        )

        # Acks & Submit
        resp = self.client.post(
            "/apply/section/acks/validate/",
            {
                "ack_sold_as_is": "on",
                "ack_quit_claim_deed": "on",
                "ack_no_title_insurance": "on",
                "ack_highest_not_guaranteed": "on",
                "ack_info_accurate": "on",
                "ack_tax_capture": "on",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertIn(resp.status_code, [200, 302])

        # Verify
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertEqual(app.purchase_type, "land_contract")
        self.assertEqual(str(app.down_payment_amount), "5000.00")


@override_settings(**E2E_SETTINGS)
class ReadyForRehabE2ETest(TestCase):
    """Walk a Ready for Rehab application through every section."""

    def test_full_flow(self):
        # Setup
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("ready_for_rehab"),
            HTTP_HX_REQUEST="true",
        )

        # Contact + Eligibility (shared)
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )

        # Offer (R4R is cash only, no purchase_type choice)
        resp = self.client.post(
            "/apply/section/offer/validate/",
            {
                "offer_amount": "25000.00",
                "has_prior_gclba_purchase": "no",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # Documents (R4R needs ID + funds + reno funding)
        self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": _fake_image("id.jpg"),
                "proof_of_funds": _fake_pdf("bank.pdf"),
                "reno_funding_proof": _fake_pdf("reno_funds.pdf"),
            },
            HTTP_HX_REQUEST="true",
        )

        # Line items (R4R specific)
        line_item_data = {
            "reno_clean_out": "1500.00",
            "reno_demolition_disposal": "2000.00",
            "reno_hvac": "3500.00",
            "reno_water_heater": "1200.00",
            "reno_plumbing": "2500.00",
            "reno_electrical": "3000.00",
            "reno_kitchen_cabinets": "4000.00",
            "reno_kitchen_appliances": "2500.00",
            "reno_bathroom_repairs": "3000.00",
            "reno_flooring": "2000.00",
            "reno_doors_int": "800.00",
            "reno_insulation": "1500.00",
            "reno_drywall_plaster": "2000.00",
            "reno_paint_wallpaper": "1000.00",
            "reno_lighting_int": "500.00",
            # Exterior
            "reno_cleanup_landscaping": "1000.00",
            "reno_roof": "5000.00",
            "reno_foundation": "0.00",
            "reno_doors_ext": "1500.00",
            "reno_windows": "4000.00",
            "reno_siding": "3000.00",
            "reno_masonry": "0.00",
            "reno_porch_decking": "2000.00",
            "reno_lighting_ext": "300.00",
            "reno_garage": "0.00",
        }
        resp = self.client.post(
            "/apply/section/line_items/validate/",
            line_item_data,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # Renovation narrative
        self.client.post(
            "/apply/section/renovation/validate/",
            {
                "intended_use": "renovate_sell",
                "renovation_description": "Full rehab: new roof, HVAC, kitchen, bath, flooring",
                "renovation_who": "ABC Contractors, Flint MI",
                "renovation_when": "8-10 months",
                "renovation_funding": "Cash reserves and CDFI loan",
            },
            HTTP_HX_REQUEST="true",
        )

        # Acks & Submit
        resp = self.client.post(
            "/apply/section/acks/validate/",
            {
                "ack_sold_as_is": "on",
                "ack_quit_claim_deed": "on",
                "ack_no_title_insurance": "on",
                "ack_highest_not_guaranteed": "on",
                "ack_info_accurate": "on",
                "ack_tax_capture": "on",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertIn(resp.status_code, [200, 302])

        # Verify
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertEqual(app.program_type, "ready_for_rehab")
        self.assertEqual(app.purchase_type, "cash")
        # Check renovation totals were stored
        self.assertIsNotNone(app.reno_interior_subtotal)
        self.assertIsNotNone(app.reno_exterior_subtotal)
        self.assertIsNotNone(app.reno_total)


@override_settings(**E2E_SETTINGS)
class VIPSpotlightE2ETest(TestCase):
    """Walk a VIP Spotlight application through every section."""

    def test_full_flow(self):
        # Setup
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("vip_spotlight"),
            HTTP_HX_REQUEST="true",
        )

        # Contact + Eligibility
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )

        # VIP Proposal (8 questions)
        resp = self.client.post(
            "/apply/section/proposal/validate/",
            {
                "vip_q1_who_and_why": (
                    "I am Jane Doe, a long-time Flint resident. I want to purchase "
                    "this property for $35,000 to restore it as my primary residence. "
                    "Contact: jane.doe@example.com, 810-555-1234."
                ),
                "vip_q2_prior_purchases": "False",
                "vip_q2_prior_detail": "",
                "vip_q3_renovation_costs_timeline": (
                    "Estimated renovation costs: $60,000 over 10 months. "
                    "Phase 1: structural/roof ($20K), Phase 2: mechanicals ($20K), "
                    "Phase 3: finishes ($20K)."
                ),
                "vip_q4_financing": (
                    "Equity: $35,000 cash (bank statement attached). "
                    "Construction loan pre-approved through First Merit for $60,000."
                ),
                "vip_q5_has_experience": "True",
                "vip_q5_experience_detail": (
                    "Renovated 3 homes in Genesee County: 123 Oak St (2022), "
                    "456 Elm Ave (2023), 789 Pine Rd (2024). Before/after photos attached."
                ),
                "vip_q6_completion_plan": "rent",
                "vip_q6_completion_detail": "Long-term rental, Section 8 accepted.",
                "vip_q7_contractor_info": "Mike's Renovations LLC, 15 years in Genesee County.",
                "vip_q8_additional_info": "Letter of support from Ward 5 Council Member attached.",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # Documents
        self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": _fake_image("id.jpg"),
                "proof_of_funds": _fake_pdf("bank.pdf"),
            },
            HTTP_HX_REQUEST="true",
        )

        # Acks & Submit (VIP has extra acks)
        resp = self.client.post(
            "/apply/section/acks/validate/",
            {
                "ack_sold_as_is": "on",
                "ack_quit_claim_deed": "on",
                "ack_no_title_insurance": "on",
                "ack_info_accurate": "on",
                "ack_tax_capture": "on",
                "ack_reconveyance_deed": "on",
                "ack_no_transfer": "on",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertIn(resp.status_code, [200, 302])

        # Verify
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertEqual(app.program_type, "vip_spotlight")
        self.assertIn("Jane Doe", app.vip_q1_who_and_why)


@override_settings(**E2E_SETTINGS)
class EligibilityGateTest(TestCase):
    """Test that the eligibility gate properly disqualifies."""

    def test_disqualified_with_delinquent_taxes(self):
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("featured_homes"),
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )

        resp = self.client.post(
            "/apply/section/eligibility/validate/",
            DISQUALIFIED_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unable to Continue")

    def test_disqualified_page_renders(self):
        resp = self.client.get("/apply/disqualified/")
        self.assertEqual(resp.status_code, 200)


@override_settings(**E2E_SETTINGS)
class DownPaymentValidationTest(TestCase):
    """Test land contract down payment minimum validation."""

    def test_down_payment_too_low(self):
        """Down payment must be >= max(10% of offer, $1000)."""
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("featured_homes"),
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )

        # $50K offer, 10% = $5,000 minimum. Try $3,000.
        resp = self.client.post(
            "/apply/section/offer/validate/",
            {
                "offer_amount": "50000.00",
                "purchase_type": "land_contract",
                "down_payment_amount": "3000.00",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        # Should contain validation error
        self.assertIn(b"Minimum down payment", resp.content)


@override_settings(**E2E_SETTINGS)
class ValidationErrorTest(TestCase):
    """Test that missing required fields return proper errors."""

    def test_empty_identity_returns_errors(self):
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/property_search/validate/",
            _property_search_data("featured_homes"),
            HTTP_HX_REQUEST="true",
        )

        # Submit empty identity form
        resp = self.client.post(
            "/apply/section/contact/validate/",
            {},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"This field is required", resp.content)
