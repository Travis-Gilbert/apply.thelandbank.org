"""
Step routing registry for the four GCLBA program paths.

Maps (program_type, purchase_type) to an ordered list of step definitions.
Each step is a dict with:
  - key: unique slug (used in templates, progress bars)
  - title: human-readable step name
  - form: string name of form class (resolved at runtime to avoid circular imports)
  - template: path to the Django template
  - is_documents: True if this step handles file uploads (no form class)

Steps 1-3 are shared across all programs (identity, property, eligibility).
Steps 4+ are program-specific and handled by the dispatcher view.
"""

# ── Shared steps (handled by dedicated views, not the dispatcher) ─

SHARED_STEPS = [
    {"key": "identity", "title": "Your Information"},
    {"key": "property", "title": "Property & Program"},
    {"key": "eligibility", "title": "Eligibility"},
]

# ── Program-specific steps (steps 4+ handled by the dispatcher) ───

FEATURED_HOMES_CASH = [
    {
        "key": "offer",
        "title": "Offer Details",
        "form": "FHOfferForm",
        "template": "apply/fh/step_offer.html",
    },
    {
        "key": "documents",
        "title": "Documents",
        "form": None,
        "template": "apply/fh/step_documents.html",
        "is_documents": True,
    },
    {
        "key": "renovation",
        "title": "Renovation Plan",
        "form": "FHRenovationNarrativeForm",
        "template": "apply/fh/step_renovation.html",
    },
    {
        "key": "acknowledgments",
        "title": "Review & Submit",
        "form": "FHAcknowledgmentsForm",
        "template": "apply/fh/step_acks.html",
    },
]

FEATURED_HOMES_LAND_CONTRACT = [
    {
        "key": "offer",
        "title": "Offer Details",
        "form": "FHOfferForm",
        "template": "apply/fh/step_offer.html",
    },
    {
        "key": "documents",
        "title": "Documents",
        "form": None,
        "template": "apply/fh/step_documents.html",
        "is_documents": True,
    },
    {
        "key": "renovation",
        "title": "Renovation Plan",
        "form": "FHRenovationNarrativeForm",
        "template": "apply/fh/step_renovation.html",
    },
    {
        "key": "homebuyer_ed",
        "title": "Homebuyer Education",
        "form": "FHHomebuyerEdForm",
        "template": "apply/fh/step_homebuyer_ed.html",
    },
    {
        "key": "acknowledgments",
        "title": "Review & Submit",
        "form": "FHAcknowledgmentsForm",
        "template": "apply/fh/step_acks.html",
    },
]

READY_FOR_REHAB = [
    {
        "key": "offer",
        "title": "Offer Details",
        "form": "R4ROfferForm",
        "template": "apply/r4r/step_offer.html",
    },
    {
        "key": "documents",
        "title": "Documents",
        "form": None,
        "template": "apply/r4r/step_documents.html",
        "is_documents": True,
    },
    {
        "key": "line_items",
        "title": "Renovation Estimate",
        "form": "R4RLineItemsForm",
        "template": "apply/r4r/step_line_items.html",
    },
    {
        "key": "renovation",
        "title": "Renovation Plan",
        "form": "R4RRenovationNarrativeForm",
        "template": "apply/r4r/step_renovation.html",
    },
    {
        "key": "acknowledgments",
        "title": "Review & Submit",
        "form": "R4RAcknowledgmentsForm",
        "template": "apply/r4r/step_acks.html",
    },
]

VIP_SPOTLIGHT = [
    {
        "key": "proposal",
        "title": "Proposal",
        "form": "VIPProposalForm",
        "template": "apply/vip/step_proposal.html",
    },
    {
        "key": "documents",
        "title": "Documents",
        "form": None,
        "template": "apply/vip/step_documents.html",
        "is_documents": True,
    },
    {
        "key": "acknowledgments",
        "title": "Review & Submit",
        "form": "VIPAcknowledgmentsForm",
        "template": "apply/vip/step_acks.html",
    },
]

# ── Route lookup ──────────────────────────────────────────────────

PROGRAM_ROUTES = {
    ("featured_homes", "cash"): FEATURED_HOMES_CASH,
    ("featured_homes", "land_contract"): FEATURED_HOMES_LAND_CONTRACT,
    ("ready_for_rehab", "cash"): READY_FOR_REHAB,
    ("vip_spotlight", "cash"): VIP_SPOTLIGHT,
}


def get_program_steps(program_type, purchase_type="cash"):
    """
    Get the program-specific step list for the given program + purchase type.

    Falls back to cash variant if the exact combo isn't found.
    Returns empty list for unrecognized programs (e.g. vacant_lot).
    """
    route = PROGRAM_ROUTES.get((program_type, purchase_type))
    if route is None:
        route = PROGRAM_ROUTES.get((program_type, "cash"), [])
    return route


def get_all_steps(program_type, purchase_type="cash"):
    """
    Get the full step list including shared steps (1-3) + program steps.

    Returns a list of step dicts. Each has at minimum 'key' and 'title'.
    Step numbering: shared steps are 1-3, program steps start at 4.
    """
    return SHARED_STEPS + get_program_steps(program_type, purchase_type)


def get_total_steps(program_type, purchase_type="cash"):
    """Total number of steps for a given program path."""
    return len(get_all_steps(program_type, purchase_type))
