"""
Shared CSV import utility for Property records.

Used by both the management command (CLI) and the admin action (UI).
Handles flexible column mapping, duplicate detection by parcel_id,
and optional replace mode that withdraws existing available properties.
"""

import csv
import io
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import Application, Property

# Flexible column name mapping — accepts common variations
COLUMN_MAP = {
    # address
    "address": "address",
    "property_address": "address",
    "property address": "address",
    "street_address": "address",
    "street address": "address",
    # parcel_id
    "parcel_id": "parcel_id",
    "parcel id": "parcel_id",
    "parcelid": "parcel_id",
    "parcel": "parcel_id",
    "pid": "parcel_id",
    # program
    "program": "program_type",
    "program_type": "program_type",
    "program type": "program_type",
    # listing_price
    "listing_price": "listing_price",
    "listing price": "listing_price",
    "price": "listing_price",
    "list_price": "listing_price",
    "list price": "listing_price",
}

# Map common program name variations to ProgramType values
PROGRAM_ALIASES = {
    "featured_homes": Application.ProgramType.FEATURED_HOMES,
    "featured homes": Application.ProgramType.FEATURED_HOMES,
    "featured": Application.ProgramType.FEATURED_HOMES,
    "fh": Application.ProgramType.FEATURED_HOMES,
    "ready_for_rehab": Application.ProgramType.READY_FOR_REHAB,
    "ready for rehab": Application.ProgramType.READY_FOR_REHAB,
    "r4r": Application.ProgramType.READY_FOR_REHAB,
    "rehab": Application.ProgramType.READY_FOR_REHAB,
    "vip_spotlight": Application.ProgramType.VIP_SPOTLIGHT,
    "vip spotlight": Application.ProgramType.VIP_SPOTLIGHT,
    "vip": Application.ProgramType.VIP_SPOTLIGHT,
    "spotlight": Application.ProgramType.VIP_SPOTLIGHT,
    "vacant_lot": Application.ProgramType.VACANT_LOT,
    "vacant lot": Application.ProgramType.VACANT_LOT,
    "vacant": Application.ProgramType.VACANT_LOT,
    "lot": Application.ProgramType.VACANT_LOT,
}


def _resolve_columns(headers):
    """Map CSV headers to internal field names. Returns {field_name: csv_index}."""
    mapping = {}
    for idx, raw_header in enumerate(headers):
        normalized = raw_header.strip().lower().replace("-", "_")
        field = COLUMN_MAP.get(normalized)
        if field and field not in mapping:
            mapping[field] = idx
    return mapping


def _parse_price(value):
    """Parse a price string like '$12,500.00' or '12500' into Decimal or None."""
    if not value:
        return None
    cleaned = value.strip().replace("$", "").replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _resolve_program(value):
    """Convert a program string to a ProgramType value, or None."""
    if not value:
        return None
    normalized = value.strip().lower()
    return PROGRAM_ALIASES.get(normalized)


def import_properties_from_csv(csv_file, replace_existing=False, batch_label=""):
    """
    Import properties from a CSV file.

    Args:
        csv_file: A file-like object (text mode) or Django UploadedFile.
        replace_existing: If True, mark current 'available' properties as
                         'withdrawn' before import.
        batch_label: Optional label for this import batch.

    Returns:
        dict with keys: created, updated, skipped, errors (list of strings)
    """
    result = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    # Handle Django UploadedFile (binary) vs text file
    if hasattr(csv_file, "read"):
        raw = csv_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig")  # Handle BOM from Excel
        text = raw
    else:
        text = csv_file

    reader = csv.reader(io.StringIO(text))

    try:
        headers = next(reader)
    except StopIteration:
        result["errors"].append("CSV file is empty.")
        return result

    col_map = _resolve_columns(headers)

    # Validate required columns
    missing = []
    for required in ("address", "parcel_id", "program_type"):
        if required not in col_map:
            missing.append(required)
    if missing:
        result["errors"].append(
            f"Missing required columns: {', '.join(missing)}. "
            f"Found columns: {', '.join(h.strip() for h in headers)}"
        )
        return result

    if not batch_label:
        batch_label = f"import-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

    # Optionally withdraw existing available properties
    if replace_existing:
        Property.objects.filter(status=Property.Status.AVAILABLE).update(
            status=Property.Status.WITHDRAWN
        )

    for row_num, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue  # Skip blank rows

        try:
            address = row[col_map["address"]].strip()
            parcel_id = row[col_map["parcel_id"]].strip()
            program_raw = row[col_map["program_type"]].strip()
        except IndexError:
            result["errors"].append(f"Row {row_num}: insufficient columns")
            continue

        if not address:
            result["errors"].append(f"Row {row_num}: missing address")
            continue
        if not parcel_id:
            result["errors"].append(f"Row {row_num}: missing parcel_id")
            continue

        program_type = _resolve_program(program_raw)
        if not program_type:
            result["errors"].append(
                f"Row {row_num}: unrecognized program '{program_raw}'"
            )
            continue

        listing_price = None
        if "listing_price" in col_map:
            listing_price = _parse_price(row[col_map["listing_price"]])

        # Upsert by parcel_id
        try:
            prop, created = Property.objects.update_or_create(
                parcel_id=parcel_id,
                defaults={
                    "address": address,
                    "program_type": program_type,
                    "listing_price": listing_price,
                    "status": Property.Status.AVAILABLE,
                    "csv_batch": batch_label,
                },
            )
            if created:
                result["created"] += 1
            else:
                result["updated"] += 1
        except Exception as e:
            result["errors"].append(f"Row {row_num}: {e}")

    return result
