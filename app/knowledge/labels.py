"""
Appendix B: Seed lexicons (dev-pool + general knowledge).
Note: Test-pool labels are deliberately omitted during development to prevent data leakage.
"""

LABELS = {
    "invoice_number": [
        "invoice no", "invoice number", "invoice #", "inv no", "inv #", "inv.",
        "invoice ref", "reference", "reference #", "ref no", "rechnungsnummer",
        "rechnungs-nr", "re-nr"
    ],
    "invoice_date": [
        "invoice date", "date of invoice", "date", "dated", "issue date",
        "issued", "issued on", "rechnungsdatum", "datum", "ausstellungsdatum"
    ],
    "due_date": [
        "due date", "payment due", "due", "pay by", "due on",
        "fälligkeitsdatum", "fällig am", "zahlbar bis"
    ],
    "terms": [
        "terms", "payment terms", "net", "due in", "within",
        "zahlungsbedingungen", "zahlungsziel"
    ],
    "subtotal": [
        "subtotal", "sub total", "sub-total", "net amount", "net total",
        "total excl", "total before tax", "taxable amount", "taxable value",
        "amount before tax", "nettobetrag", "summe netto", "zwischensumme"
    ],
    "tax": [
        "vat", "sales tax", "tax", "gst", "cgst", "sgst", "igst",
        "total vat", "total tax", "mwst", "mehrwertsteuer", "ust", "umsatzsteuer"
    ],
    "total_t1": [
        "amount due", "balance due", "total due", "amount payable",
        "total payable", "zu zahlen"
    ],
    "total_t2": [
        "grand total", "invoice total", "total incl", "gesamtbetrag",
        "rechnungsbetrag", "endbetrag"
    ],
    "total_t3": [
        "total"
    ],
    "exclude_invoice_number": [
        "po", "p.o.", "purchase order", "order no", "order number", "customer no",
        "customer ref", "account no", "vat no", "gstin", "tax id", "iban", "phone", "tel", "page"
    ],
    "exclude_invoice_date": [
        "order date", "delivery date", "ship date", "shipped", "date of supply",
        "tax point", "po date"
    ],
    "customer_block_markers": [
        "bill to", "billed to", "sold to", "ship to", "customer", "invoice to",
        "kunde", "rechnungsempfänger"
    ]
}
