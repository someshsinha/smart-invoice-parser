"""
Centralized catalog of warning strings.
Defined in a single place to maintain consistency across the entire codebase.
"""

def warn_ambiguous_date(raw: str, order: str, country: str) -> str:
    return f"Date {raw} read as {order}-first ({country} vendor)."

def warn_terms_due_date(terms: str) -> str:
    return f"Due date derived from terms {terms}."

def warn_conflicting_due_date(printed_iso: str, terms: str, terms_iso: str) -> str:
    return f"Printed due date {printed_iso} differs from terms {terms} ({terms_iso}); used printed date."

def warn_arithmetic_mismatch(subtotal: float, tax: float, total: float) -> str:
    return f"Subtotal plus tax does not equal total ({subtotal:.2f} + {tax:.2f} != {total:.2f})."

def warn_no_currency(canonical_currency: str) -> str:
    return f"No currency printed; assumed {canonical_currency} from vendor."

def warn_currency_mismatch(printed_cur: str, vendor_cur: str) -> str:
    return f"Printed currency {printed_cur} differs from vendor default {vendor_cur}."

def warn_unknown_vendor() -> str:
    return "Vendor name not in the canonical list."

def warn_brand_only_vendor(canonical: str) -> str:
    return f"Vendor matched on brand name only ({canonical})."

def warn_vendor_resembles(canonical: str) -> str:
    return f"Vendor name resembles {canonical} but does not match; reported as unknown."

def warn_no_due_date_or_terms() -> str:
    return "No due date or payment terms found."

def warn_non_invoice_doctype(doctype: str) -> str:
    return f"Document appears to be a {doctype}, not an invoice."

def warn_no_text_layer() -> str:
    return "No text layer found; scanned documents are out of scope."

def warn_multiple_invoice_numbers(chosen: str) -> str:
    return f"Multiple possible invoice numbers found; chose {chosen}."

def warn_field_extraction_failed(field_name: str) -> str:
    return f"Could not extract {field_name}."
