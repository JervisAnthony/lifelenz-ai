"""Bearer-protected structured CSV import route."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from lifelenz.api.dependencies import ApiContainer, get_api_container, get_current_user
from lifelenz.api.import_schemas import (
    CsvImportDuplicateResponse,
    CsvImportIssueResponse,
    CsvImportRequest,
    CsvImportResponse,
)
from lifelenz.api.schemas import ApiErrorResponse
from lifelenz.identity import UserAccount

ContainerDependency = Annotated[ApiContainer, Depends(get_api_container)]
CurrentUserDependency = Annotated[UserAccount, Depends(get_current_user)]


def import_csv(
    request: CsvImportRequest,
    account: CurrentUserDependency,
    container: ContainerDependency,
) -> CsvImportResponse:
    """Validate or commit one versioned CSV document for the authenticated account."""
    report = container.authenticated_wellness_csv_import_service.import_csv(
        account.user_id,
        schema_version=request.schema_version,
        record_type=request.record_type,
        content=request.content,
        commit=request.mode == "commit",
    )
    return CsvImportResponse(
        schema_version=report.schema_version,
        record_type=report.record_type,
        mode=request.mode,
        total_rows=report.total_rows,
        valid_rows=report.valid_rows,
        invalid_rows=report.invalid_rows,
        duplicate_rows=report.duplicate_rows,
        ready_rows=report.ready_rows,
        imported_rows=report.imported_rows,
        can_commit=report.can_commit,
        issues=tuple(
            CsvImportIssueResponse(
                row_number=issue.row_number,
                field=issue.field,
                code=issue.code,
                message=issue.message,
            )
            for issue in report.issues
        ),
        duplicates=tuple(
            CsvImportDuplicateResponse(
                row_number=duplicate.row_number,
                reason=duplicate.reason,
            )
            for duplicate in report.duplicates
        ),
    )


def create_imports_router() -> APIRouter:
    """Return authenticated CSV import routes."""
    router = APIRouter(prefix="/imports", tags=["imports"])
    router.add_api_route(
        "/csv",
        import_csv,
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        response_model=CsvImportResponse,
        responses={
            400: {"model": ApiErrorResponse},
            401: {"model": ApiErrorResponse},
            404: {"model": ApiErrorResponse},
            422: {"model": ApiErrorResponse},
        },
        operation_id="imports_csv",
        summary="Validate or import wellness records from CSV",
    )
    return router
