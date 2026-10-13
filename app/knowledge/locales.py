"""
Country and locale mapping rules.
"""

COUNTRY_LOCALES = {
    "United Kingdom": {"date_order": "DMY", "currency": "GBP", "decimal": "."},
    "United States": {"date_order": "MDY", "currency": "USD", "decimal": "."},
    "Germany": {"date_order": "DMY", "currency": "EUR", "decimal": ","},
    "Japan": {"date_order": "DMY", "currency": "JPY", "decimal": None},
    "India": {"date_order": "DMY", "currency": "INR", "decimal": "."},
}
