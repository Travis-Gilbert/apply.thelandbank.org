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
}


def _fake_pdf(name="test.pdf"):
    """Create a minimal fake PDF for upload testing."""
    content = b"%PDF-1.4 fake"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _fake_image(name="id.jpg"):
    """Create a minimal fake JPEG for upload testing."""
    # Minimal JPEG header
    content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    return SimpleUploadedFile(name, content, content_type="image/jpeg")


# ── Shared identity/property/eligibility data ─────────────────────

IDENTITY_DATA = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone": "810-555-1234",
    "mailing_address": "123 Test Street",
    "mailing_city": "Flint",
    "mailing_state": "MI",
    "mailing_zip": "48502",
    "preferred_contact": "email",
}

PROPERTY_DATA = {
    "property_address": "456 Main St, Flint, MI",
    "parcel_id": "41-20-100-001",
    "attended_open_house": "no",
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

        # ── Step 2: Select program ───────────────────────────────
        resp = self.client.post(
            "/apply/section/program-select/",
            {"program": "featured_homes"},
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

        # ── Step 4: Property ─────────────────────────────────────
        resp = self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 5: Eligibility ──────────────────────────────────
        resp = self.client.post(
            "/apply/section/eligibility/validate/",
            ELIGIBLE_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        # Should NOT redirect to disqualified
        self.assertNotIn(b"disqualified", resp.content.lower())
        self.assertIn(b"Offer", resp.content)

        # ── Step 6: Offer details (cash) ─────────────────────────
        resp = self.client.post(
            "/apply/section/offer/validate/",
            {
                "offer_amount": "45000.00",
                "purchase_type": "cash",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 7: Documents ────────────────────────────────────
        resp = self.client.post(
            "/apply/section/documents/validate/",
            {
                "photo_id": _fake_image("photo_id.jpg"),
                "proof_of_funds": _fake_pdf("bank_statement.pdf"),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 8: Renovation narrative ─────────────────────────
        resp = self.client.post(
            "/apply/section/renovation/validate/",
            {
                "intended_use": "renovate_move_in",
                "first_home_status": "first_home",
                "renovation_plans": "Replace roof, update kitchen and bathrooms",
                "renovation_who": "Licensed contractor",
                "renovation_when": "Within 6 months of purchase",
                "renovation_financing": "Personal savings and home improvement loan",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)

        # ── Step 9: Acknowledgments & Submit ─────────────────────
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
        # Select program
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/program-select/",
            {"program": "featured_homes"},
            HTTP_HX_REQUEST="true",
        )

        # Contact
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )

        # Property
        self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
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
                "first_home_status": "neither",
                "renovation_plans": "Full interior renovation",
                "renovation_who": "Self and family",
                "renovation_when": "12 months",
                "renovation_financing": "Savings",
            },
            HTTP_HX_REQUEST="true",
        )

        # Homebuyer education (land contract only)
        self.client.post(
            "/apply/section/homebuyer_ed/validate/",
            {
                "homebuyer_ed_completed": "yes",
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
            "/apply/section/program-select/",
            {"program": "ready_for_rehab"},
            HTTP_HX_REQUEST="true",
        )

        # Contact + Property + Eligibility (shared)
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
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
            "clean_out": "1500.00",
            "demolition_disposal": "2000.00",
            "hvac": "3500.00",
            "water_heater": "1200.00",
            "plumbing": "2500.00",
            "electrical": "3000.00",
            "kitchen_cabinets": "4000.00",
            "kitchen_appliances": "2500.00",
            "bathroom_repairs": "3000.00",
            "flooring": "2000.00",
            "interior_doors": "800.00",
            "insulation": "1500.00",
            "drywall_plaster": "2000.00",
            "paint_wallpaper": "1000.00",
            "interior_lighting": "500.00",
            # Exterior
            "landscaping": "1000.00",
            "roof": "5000.00",
            "foundation": "0.00",
            "exterior_doors": "1500.00",
            "windows": "4000.00",
            "siding": "3000.00",
            "masonry": "0.00",
            "porch_decking": "2000.00",
            "exterior_lighting": "300.00",
            "garage": "0.00",
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
                "renovation_plans": "Full rehab: new roof, HVAC, kitchen, bath, flooring",
                "renovation_who": "ABC Contractors, Flint MI",
                "renovation_when": "8-10 months",
                "renovation_financing": "Cash reserves and CDFI loan",
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
        self.assertIsNotNone(app.interior_subtotal)
        self.assertIsNotNone(app.exterior_subtotal)
        self.assertIsNotNone(app.total_renovation_cost)


@override_settings(**E2E_SETTINGS)
class VIPSpotlightE2ETest(TestCase):
    """Walk a VIP Spotlight application through every section."""

    def test_full_flow(self):
        # Setup
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/program-select/",
            {"program": "vip_spotlight"},
            HTTP_HX_REQUEST="true",
        )

        # Contact + Property + Eligibility
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
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
                "q1_who_and_why": (
                    "I am Jane Doe, a long-time Flint resident. I want to purchase "
                    "this property for $35,000 to restore it as my primary residence. "
                    "Contact: jane.doe@example.com, 810-555-1234."
                ),
                "q2_prior_purchase": "no",
                "q2_prior_details": "",
                "q3_reno_costs_timeline": (
                    "Estimated renovation costs: $60,000 over 10 months. "
                    "Phase 1: structural/roof ($20K), Phase 2: mechanicals ($20K), "
                    "Phase 3: finishes ($20K)."
                ),
                "q4_financing": (
                    "Equity: $35,000 cash (bank statement attached). "
                    "Construction loan pre-approved through First Merit for $60,000."
                ),
                "q5_experience": "yes",
                "q5_experience_details": (
                    "Renovated 3 homes in Genesee County: 123 Oak St (2022), "
                    "456 Elm Ave (2023), 789 Pine Rd (2024). Before/after photos attached."
                ),
                "q6_completion_plans": "rent",
                "q6_completion_details": "Long-term rental, Section 8 accepted.",
                "q7_contractor": "Mike's Renovations LLC, 15 years in Genesee County.",
                "q8_additional": "Letter of support from Ward 5 Council Member attached.",
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
        self.assertIn("Jane Doe", app.q1_who_and_why)


@override_settings(**E2E_SETTINGS)
class EligibilityGateTest(TestCase):
    """Test that the eligibility gate properly disqualifies."""

    def test_disqualified_with_delinquent_taxes(self):
        self.client.get("/apply/")
        self.client.post(
            "/apply/section/program-select/",
            {"program": "featured_homes"},
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
            HTTP_HX_REQUEST="true",
        )

        resp = self.client.post(
            "/apply/section/eligibility/validate/",
            DISQUALIFIED_DATA,
            HTTP_HX_REQUEST="true",
        )
        # Should return HX-Redirect header pointing to disqualified page
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["HX-Redirect"], "/apply/disqualified/")

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
            "/apply/section/program-select/",
            {"program": "featured_homes"},
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/contact/validate/",
            IDENTITY_DATA,
            HTTP_HX_REQUEST="true",
        )
        self.client.post(
            "/apply/section/property/validate/",
            PROPERTY_DATA,
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
            "/apply/section/program-select/",
            {"program": "featured_homes"},
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
