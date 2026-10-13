import pytest
from pathlib import Path


def test_dockerfile_structure():
    repo_root = Path(__file__).resolve().parent.parent
    dockerfile = repo_root / "Dockerfile"
    dockerignore = repo_root / ".dockerignore"

    assert dockerfile.exists(), "Dockerfile must exist at repository root"
    assert dockerignore.exists(), ".dockerignore must exist at repository root"

    content = dockerfile.read_text(encoding="utf-8")

    # Assert key production container requirements
    assert "FROM python:3.11-slim" in content or "FROM python:3.12-slim" in content
    assert "EXPOSE 8000" in content
    assert "HEALTHCHECK" in content
    assert "http://localhost:8000/health" in content
    assert "uvicorn" in content
    assert "app.main:app" in content
    assert "8000" in content

    # Assert dockerignore guards
    ignore_content = dockerignore.read_text(encoding="utf-8")
    assert ".git" in ignore_content
    assert "tests" in ignore_content
    assert "data" in ignore_content


def test_code_tour_content():
    repo_root = Path(__file__).resolve().parent.parent
    code_tour = repo_root / "docs" / "CODE_TOUR.md"

    assert code_tour.exists(), "docs/CODE_TOUR.md must exist"

    content = code_tour.read_text(encoding="utf-8")

    # Verify request flow section
    assert "Request Flow" in content
    assert "POST /extract" in content

    # Verify core modules covered
    modules = [
        "app/reader/pdf_text.py",
        "app/extract/doctype.py",
        "app/extract/vendor.py",
        "app/extract/candidates.py",
        "app/extract/amounts.py",
        "app/extract/confidence.py",
    ]
    for mod in modules:
        assert mod in content, f"Module {mod} must be documented in CODE_TOUR.md"

    # Verify guidance sections
    assert "Debug Mode" in content or "?debug=1" in content
    assert "How to Add a New Vendor" in content
    assert "How to Add a New Label" in content
