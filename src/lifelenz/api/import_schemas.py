"""Strict schemas for authenticated CSV wellness-data imports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lifelenz.ingestion import CSV_SCHEMA_VERSION, MAX_CSV_BYTES, CsvImportRecordType


class _StrictImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CsvImportRequest(_StrictImportModel):
    """One versioned CSV document to validate or commit for the current account."""

    schema_version: int = Field(default=CSV_SCHEMA_VERSION, ge=1)
    record_type: CsvImportRecordType
    mode: Literal["validate", "commit"] = "validate"
    content: str = Field(min_length=1, max_length=MAX_CSV_BYTES)


class CsvImportIssueResponse(_StrictImportModel):
    """Actionable validation issue tied to a CSV row and field where possible."""

    row_number: int | None
    field: str | None
    code: str
    message: str


class CsvImportDuplicateResponse(_StrictImportModel):
    """Valid row skipped because its semantic record already exists."""

    row_number: int
    reason: Literal["existing_record", "earlier_row"]


class CsvImportResponse(_StrictImportModel):
    """Validation/import report without echoing sensitive CSV row payloads."""

    schema_version: int
    record_type: CsvImportRecordType
    mode: Literal["validate", "commit"]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    ready_rows: int
    imported_rows: int
    can_commit: bool
    issues: tuple[CsvImportIssueResponse, ...]
    duplicates: tuple[CsvImportDuplicateResponse, ...]
