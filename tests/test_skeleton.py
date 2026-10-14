import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import InvoiceExtractionResponse


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ui_index_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Smart Invoice Parser" in response.text
    assert "html" in response.headers["content-type"]


def test_extract_missing_file_parameter(client):
    # Missing file parameter should return 400 per section 3.5
    response = client.post("/extract")
    assert response.status_code == 400
    assert "error" in response.json()


def test_extract_non_pdf_file(client):
    # Non-PDF content (missing %PDF- magic bytes) should return 400
    files = {"file": ("test.txt", b"Hello world, this is plain text.", "text/plain")}
    response = client.post("/extract", files=files)
    assert response.status_code == 400
    assert "error" in response.json()
    assert "%PDF-" in response.json()["error"]


def test_extract_valid_pdf_structure(client):
    # Minimal mock PDF content starting with %PDF-
    mock_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    files = {"file": ("invoice.pdf", mock_pdf, "application/pdf")}
    response = client.post("/extract", files=files)
    assert response.status_code == 200
    data = response.json()

    # Validate against Pydantic schema
    validated = InvoiceExtractionResponse.model_validate(data)
    assert validated.vendor is not None
    assert isinstance(validated.warnings, list)

    # Check all 8 confidence keys are present
    conf = data["confidence"]
    expected_fields = [
        "vendor",
        "invoice_number",
        "invoice_date",
        "due_date",
        "currency",
        "subtotal",
        "tax",
        "total",
    ]
    for f in expected_fields:
        assert f in conf
        assert 0.0 <= conf[f] <= 1.0


def test_offline_constraint_blocks_network():
    import socket

    with pytest.raises(RuntimeError, match="Network call blocked by offline constraint"):
        s = socket.socket()
        s.connect(("8.8.8.8", 53))


def test_extract_debug_parameter(client):
    from pathlib import Path
    pdf_bytes = (Path("samples") / "northwind_1042.pdf").read_bytes()
    files = {"file": ("northwind.pdf", pdf_bytes, "application/pdf")}

    # 1. Without debug query param
    resp_no_debug = client.post("/extract", files=files)
    assert resp_no_debug.status_code == 200
    assert resp_no_debug.json().get("debug") is None

    # 2. With debug=true
    files = {"file": ("northwind.pdf", pdf_bytes, "application/pdf")}
    resp_debug = client.post("/extract?debug=true", files=files)
    assert resp_debug.status_code == 200
    debug_payload = resp_debug.json().get("debug")
    assert debug_payload is not None
    assert "timings_ms" in debug_payload
    assert "document" in debug_payload
    assert "arithmetic" in debug_payload
    assert debug_payload["arithmetic"]["is_balanced"] is True


def test_schema_non_invoice_delivery_note_all_keys_present(client):
    from tests.test_reader import create_simple_test_pdf
    pdf = create_simple_test_pdf([
        "NORTHWIND TRADERS LTD",
        "DELIVERY NOTE # DN-9912",
        "Packing slip for delivery",
        "Sold to: Bruviti Services Pvt Ltd"
    ])
    res = client.post("/extract", files={"file": ("delivery.pdf", pdf, "application/pdf")})
    assert res.status_code == 200
    data = res.json()

    # All top-level keys must be present
    required_keys = ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total", "confidence", "warnings"]
    for k in required_keys:
        assert k in data, f"Missing required top-level key: {k}"

    # Non-invoice fields must be null
    assert data["vendor"] == "Northwind Traders"
    assert data["invoice_number"] is None
    assert data["invoice_date"] is None
    assert data["due_date"] is None
    assert data["currency"] is None
    assert data["subtotal"] is None
    assert data["tax"] is None
    assert data["total"] is None

    # All 8 confidence keys must be present
    conf = data["confidence"]
    assert len(conf) == 8
    for k in ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total"]:
        assert k in conf
        assert conf[k] == 0.0 or (k == "vendor" and conf[k] > 0.0)

    # Must contain delivery note warning
    assert any("delivery note" in w.lower() for w in data["warnings"])


def test_schema_missing_due_date_and_tax_preserves_keys(client):
    from tests.test_reader import create_simple_test_pdf
    # Invoice with missing due date/terms and no tax line
    pdf = create_simple_test_pdf([
        "Kestrel Components Inc.",
        "Invoice No: KC-4401",
        "Invoice Date: 09/03/2026",
        "Sold to: Bruviti Services Pvt Ltd",
        "Subtotal: USD 145.00",
        "Total: USD 145.00"
    ])
    res = client.post("/extract", files={"file": ("invoice.pdf", pdf, "application/pdf")})
    assert res.status_code == 200
    data = res.json()

    required_keys = ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total", "confidence", "warnings"]
    for k in required_keys:
        assert k in data, f"Missing required key: {k}"

    assert data["vendor"] == "Kestrel Components"
    assert data["invoice_number"] == "KC-4401"
    assert data["invoice_date"] == "2026-09-03"
    assert data["due_date"] is None
    assert data["tax"] is None
    assert data["subtotal"] == 145.0
    assert data["total"] == 145.0

    # Confidence must have all 8 keys
    conf = data["confidence"]
    assert len(conf) == 8
    for k in ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total"]:
        assert k in conf
        assert isinstance(conf[k], float)
    assert conf["due_date"] == 0.0
    assert conf["tax"] == 0.0


