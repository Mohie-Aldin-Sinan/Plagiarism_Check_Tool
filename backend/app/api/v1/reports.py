"""Reports endpoint — accepts detection results and returns a downloadable .xlsx report."""

import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.reports import (
    DetectionResult,
    classify_risk,
    generate_report_bytes,
    generate_report_csv_bytes,
    _OPENPYXL_AVAILABLE,
)
import zipfile

app = APIRouter()


class ResultItem(BaseModel):
    text: str
    is_duplicate: bool
    similarity_scores: Dict[str, float] = {}
    source: Optional[str] = None
    risk_level: str = "none"
    detection_method: Optional[str] = None
    notes: Optional[str] = None


class ReportRequest(BaseModel):
    results: List[ResultItem]
    filename: str = "plagiarism_report"
    format: str = "xlsx"


# Matches the exact shape returned by POST /api/v1/web-scan/scan
class WebScanMatchItem(BaseModel):
    url: str
    title: str
    snippet: str
    page_excerpt: str
    similarity_scores: Dict[str, float] = {}
    best_score: float = 0.0
    fingerprint: Dict[str, Any] = {}


class WebScanReportRequest(BaseModel):
    submitted_text: str
    is_plagiarism: bool
    best_score: float
    best_url: Optional[str] = None
    matches: List[WebScanMatchItem] = []
    filename: str = "web_scan_report"
    format: str = "xlsx"


_EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_report_response(
    results: List[DetectionResult],
    base_filename: str,
    fmt: str | None,
):
    selected = (fmt or "xlsx").lower()

    if selected == "none":
        return None

    if selected not in {"xlsx", "excel", "csv", "both"}:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'xlsx', 'csv', 'both', or 'none'")

    if selected in {"xlsx", "excel"}:
        if not _OPENPYXL_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="openpyxl not installed. Run: pip install openpyxl",
            )
        report_bytes = generate_report_bytes(results)
        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type=_EXCEL_MEDIA_TYPE,
            headers={"Content-Disposition": f"attachment; filename={base_filename}.xlsx"},
        )

    if selected == "csv":
        report_bytes = generate_report_csv_bytes(results)
        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={base_filename}.csv"},
        )

    # selected == "both"
    if not _OPENPYXL_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="openpyxl not installed. Run: pip install openpyxl",
        )
    excel_bytes = generate_report_bytes(results)
    csv_bytes = generate_report_csv_bytes(results)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_filename}.xlsx", excel_bytes)
        zf.writestr(f"{base_filename}.csv", csv_bytes)

    return StreamingResponse(
        io.BytesIO(zip_buffer.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={base_filename}_reports.zip"},
    )


@app.get("/")
async def reports_root():
    return {
        "message": "Reports endpoint",
        "available": _OPENPYXL_AVAILABLE,
        "install_hint": None if _OPENPYXL_AVAILABLE else "Run: pip install openpyxl",
    }


@app.post("/download")
async def download_report(request: ReportRequest):
    """Generate a styled .xlsx report from provided detection results and return it as a file download."""
    if not request.results:
        raise HTTPException(status_code=400, detail="Provide at least one result")

    output_format = (request.format or "xlsx").lower()

    detection_results = [
        DetectionResult(
            text=r.text,
            is_duplicate=r.is_duplicate,
            similarity_scores=r.similarity_scores,
            source=r.source,
            risk_level=r.risk_level,
            detection_method=r.detection_method,
            notes=r.notes,
        )
        for r in request.results
    ]

    response = _build_report_response(
        detection_results,
        base_filename=request.filename.strip() or "plagiarism_report",
        fmt=output_format,
    )
    if response:
        return response


@app.post("/from-web-scan")
async def report_from_web_scan(request: WebScanReportRequest):
    """Generate a report directly from the web scan response — one row per matched source.

    Paste the full JSON from POST /api/v1/web-scan/scan here (with submitted_text included).
    If no matches, a single clean row is generated.
    """
    detection_results = []

    if request.matches:
        for m in request.matches:
            domain = m.fingerprint.get("domain", "")
            published = m.fingerprint.get("published_at")
            notes = f"Title: {m.title}"
            if domain:
                notes += f" | Domain: {domain}"
            if published:
                notes += f" | Published: {published}"

            detection_results.append(DetectionResult(
                text=request.submitted_text,
                is_duplicate=True,
                similarity_scores=m.similarity_scores,
                source=m.url,
                risk_level=classify_risk(m.best_score),
                detection_method="web_scan",
                notes=notes,
            ))
    else:
        # No matches found — single clean row
        detection_results.append(DetectionResult(
            text=request.submitted_text,
            is_duplicate=False,
            risk_level="none",
            detection_method="web_scan",
        ))

    response = _build_report_response(
        detection_results,
        base_filename=request.filename.strip() or "web_scan_report",
        fmt=request.format,
    )
    if response:
        return response

