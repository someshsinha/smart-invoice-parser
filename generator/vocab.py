"""
Synthetic Invoice Generator Vocabulary.
Supplies realistic line items, addresses, decoy vendor names, and customer metadata.
"""

LINE_ITEMS = [
    ("Pallet wrap, 500mm", 18.50),
    ("Corrugated boxes, large", 2.35),
    ("Packing tape, brown", 1.90),
    ("Heavy duty bubble wrap, 100m", 24.00),
    ("Poly mailers 10x13 inch", 0.45),
    ("Bearing kit 6204-2RS", 14.50),
    ("Drive belt A-42", 15.70),
    ("Hydraulic seal kit", 38.00),
    ("Stainless steel bolts M8x25", 0.60),
    ("Industrial grease cartridge", 8.20),
    ("Precision CNC machined bracket", 45.00),
    ("Pneumatic fitting 1/4 inch", 3.20),
    ("Vibration dampening mount", 12.50),
    ("Packaging foam inserts", 1.80),
    ("Shipping and handling", 18.00),
]

CUSTOMER_INFO = {
    "name": "Bruviti Services Pvt Ltd",
    "address": "Tower B, Cyber City, Phase III, Gurugram, HR 122002, India",
    "tax_id": "GSTIN 07AAAAA0000A1Z5",
}

# Decoys from PRD §8.3:
# (a) Same brand token, conflicting generic word -> unknown with resembles warning
# (b) Different brand, same generic word -> unknown
DECOY_VENDORS = [
    # Same brand, conflicting generic
    {"name": "Northwind Logistics Ltd", "resembles": "Northwind Traders"},
    {"name": "Meridian Packaging GmbH", "resembles": "Meridian Industrial"},
    {"name": "Kestrel Aerospace Inc", "resembles": "Kestrel Components"},
    {"name": "Sakura Logistics KK", "resembles": "Sakura Precision"},
    # Different brand, same generic
    {"name": "Pinewood Packaging Ltd", "resembles": None},
    {"name": "Falcon Components Inc", "resembles": None},
    {"name": "Meadowbank Industrial GmbH", "resembles": None},
    {"name": "Apex Supplies Ltd", "resembles": None},
]

VENDOR_ADDRESSES = {
    "Northwind Traders": "14 Quay Street, Bristol BS1 4DB, United Kingdom",
    "Blue Harbour Logistics": "Unit 4, Royal Docks, London E16 2QY, United Kingdom",
    "Kestrel Components": "880 Industrial Pkwy, Dayton OH 45402, USA",
    "Meridian Industrial": "Industriestraße 10, 70173 Stuttgart, Deutschland",
    "Sakura Precision": "2-3-1 Marunouchi, Chiyoda-ku, Tokyo 100-0005, Japan",
    "Pinecrest Packaging": "Plot 42, Peenya Industrial Area, Bengaluru 560058, India",
}


def sample_line_items(rng, n: int = 3):
    """Samples n items from vocabulary using provided RNG."""
    return rng.sample(LINE_ITEMS, k=min(n, len(LINE_ITEMS)))

