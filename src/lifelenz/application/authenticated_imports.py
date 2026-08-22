"""Authenticated CSV import orchestration for profile-owned wellness records."""

from dataclasses import dataclass
from typing import Literal

from lifelenz.application.authenticated_records import AuthenticatedWellnessRecordService
from lifelenz.application.exceptions import ApplicationValidationError
from lifelenz.identity import UserId
from lifelenz.ingestion import (
    CsvImportIssue,
    CsvImportRecordType,
    WellnessCsvParser,
    wellness_record_identity,
)
from lifelenz.repositories import WellnessRecord


@dataclass(frozen=True, slots=True)
class CsvImportDuplicate:
    """One valid CSV row skipped because the same semantic record already exists."""

    row_number: int
    reason: Literal["existing_record", "earlier_row"]


@dataclass(frozen=True, slots=True)
class CsvImportReport:
    """Deterministic validation/import report returned without exposing record payloads."""

    schema_version: int
    record_type: CsvImportRecordType
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    ready_rows: int
    imported_rows: int
    can_commit: bool
    issues: tuple[CsvImportIssue, ...]
    duplicates: tuple[CsvImportDuplicate, ...]


class AuthenticatedWellnessCsvImportService:
    """Validate, deduplicate, and optionally persist CSV records for one account."""

    def __init__(
        self,
        record_service: AuthenticatedWellnessRecordService,
        parser: WellnessCsvParser | None = None,
    ) -> None:
        if not isinstance(record_service, AuthenticatedWellnessRecordService):
            raise ApplicationValidationError(
                "record_service must be an AuthenticatedWellnessRecordService"
            )
        if parser is not None and not isinstance(parser, WellnessCsvParser):
            raise ApplicationValidationError("parser must be a WellnessCsvParser or None")
        self._record_service = record_service
        self._parser = WellnessCsvParser() if parser is None else parser

    def import_csv(
        self,
        user_id: UserId,
        *,
        schema_version: int,
        record_type: CsvImportRecordType,
        content: str,
        commit: bool = False,
    ) -> CsvImportReport:
        """Validate one CSV file and persist only when the complete file is valid.

        Duplicate rows are not validation failures. Exact semantic duplicates are
        skipped both against existing owned records and earlier valid rows in the
        same file. If any validation issue exists, ``commit=True`` still performs
        no writes so a malformed file cannot produce a partial validation import.
        """
        if not isinstance(user_id, UserId):
            raise ApplicationValidationError(f"user_id must be a UserId; got {user_id!r}")
        if type(commit) is not bool:
            raise ApplicationValidationError(f"commit must be a bool; got {commit!r}")
        if not isinstance(record_type, CsvImportRecordType):
            raise ApplicationValidationError(
                f"record_type must be a CsvImportRecordType; got {record_type!r}"
            )

        existing_records = self._record_service.list_records(user_id)
        parsed = self._parser.parse(
            schema_version=schema_version,
            record_type=record_type,
            content=content,
        )

        existing_identities = {wellness_record_identity(record) for record in existing_records}
        batch_identities: set[tuple[object, ...]] = set()
        ready: list[WellnessRecord] = []
        duplicates: list[CsvImportDuplicate] = []

        for entry in parsed.records:
            identity = wellness_record_identity(entry.record)
            if identity in existing_identities:
                duplicates.append(CsvImportDuplicate(entry.row_number, "existing_record"))
                continue
            if identity in batch_identities:
                duplicates.append(CsvImportDuplicate(entry.row_number, "earlier_row"))
                continue
            batch_identities.add(identity)
            ready.append(entry.record)

        can_commit = not parsed.issues
        imported_rows = 0
        if commit and can_commit:
            for record in ready:
                self._record_service.create_record(user_id, record)
                imported_rows += 1

        return CsvImportReport(
            schema_version=parsed.schema_version,
            record_type=parsed.record_type,
            total_rows=parsed.total_rows,
            valid_rows=parsed.valid_rows,
            invalid_rows=parsed.invalid_rows,
            duplicate_rows=len(duplicates),
            ready_rows=len(ready),
            imported_rows=imported_rows,
            can_commit=can_commit,
            issues=parsed.issues,
            duplicates=tuple(duplicates),
        )
