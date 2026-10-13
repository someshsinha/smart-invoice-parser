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
