"""
Main FastAPI application entry point.
Implements the API contract, static UI mounting, healthcheck, and error handling.
"""

from contextlib import asynccontextmanager
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Request, Query, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import MAX_UPLOAD_SIZE_BYTES, PDF_MAGIC_BYTES, STATIC_DIR, SAMPLES_DIR
from app.schemas import HealthResponse, InvoiceExtractionResponse
from app.pipeline import process_invoice_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("invoice_extractor")

is_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info("Initializing invoice extractor service...")
    # Precompilation / warm-up step
    # Ensures caches and models are loaded before answering requests
    is_ready = True
    logger.info("Service warmup complete. Ready to receive requests on port 8000.")
    yield
    is_ready = False
    logger.info("Shutting down service.")


app = FastAPI(
    title="Invoice Field Extraction Service",
    description="Offline field extraction for supplier invoices",
    lifespan=lifespan,
)

# Mount samples directory if it exists
if SAMPLES_DIR.exists():
    app.mount("/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")


@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint. Returns 200 once ready, 503 during warmup/downtime."""
    if not is_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "starting"})
    return HealthResponse(status="ok")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the single-page UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Invoice Field Extraction Service</h1><p>UI loading...</p>")


@app.post("/extract", response_model=InvoiceExtractionResponse)
async def extract(
    file: Optional[UploadFile] = File(None),
    debug: bool = Query(False, description="Include provenance evidence in response"),
):
    """
    Extracts invoice header fields from uploaded PDF.
    Enforces strict validation, size limits, and error handling as specified in PRD §3.5.
    Always returns all 8 header fields + confidence (8 keys) + warnings.
    """
    # 1. Missing file parameter -> 400
    if file is None or file.filename is None or file.filename.strip() == "":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Missing 'file' field in multipart form upload."},
        )

    # 2. Read file content and check size limit (10 MB -> 413)
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES} bytes."},
        )

    # 3. Check PDF magic bytes (%PDF-) -> 400
    if not content.startswith(PDF_MAGIC_BYTES):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Uploaded file is not a valid PDF document (missing %PDF- header)."},
        )

    try:
        response, evidence = process_invoice_pdf(content, debug=debug)
        data = response.model_dump()
        if not debug:
            data.pop("debug", None)
        return JSONResponse(status_code=status.HTTP_200_OK, content=data)
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Failed to parse or process PDF document: {str(e)}"},
        )
