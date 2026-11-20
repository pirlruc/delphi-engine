"""FastAPI application factory."""

import os
import secrets
from datetime import date
from typing import Annotated
from uuid import UUID

from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse
from delphi_contracts.enums import NeighborhoodMode
from delphi_contracts.neighborhood import Neighborhood
from delphi_contracts.paths import ContextLeakError, PathProposal, PathRequest
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from delphi.catalog import Catalog, MemoryCatalog
from delphi.ports import Embedder, Extractor, Generator
from delphi.services import (
    ConsentError,
    MissingDependencyError,
    generate_paths,
    upload_pdf,
)

__all__ = ["AppContainer", "create_app"]

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class AppContainer:
    """Runtime collaborators for the API.

    Attributes:
        catalog: Work store.
        extractor: Optional Daedalus extractor.
        embedder: Optional Daedalus embedder.
        generator: Optional Prometheus generator.
        api_key: Shared secret required on /v1 routes. Empty rejects every call.
    """

    def __init__(
        self,
        catalog: Catalog | None = None,
        extractor: Extractor | None = None,
        embedder: Embedder | None = None,
        generator: Generator | None = None,
        api_key: str | None = None,
    ) -> None:
        """Store collaborators.

        Args:
            catalog: Catalog implementation.
            extractor: PDF extractor.
            embedder: Content-graph embedder.
            generator: Path generator.
            api_key: Required X-API-Key. None reads DELPHI_API_KEY.
        """
        self.catalog = catalog or MemoryCatalog()
        self.extractor = extractor
        self.embedder = embedder
        self.generator = generator
        self.api_key = os.environ.get("DELPHI_API_KEY", "") if api_key is None else api_key


def create_app(container: AppContainer | None = None) -> FastAPI:
    """Build the prototype REST app.

    Args:
        container: Wired collaborators. Defaults to an empty memory catalog.

    Returns:
        FastAPI application.
    """
    state = container or AppContainer()
    app = FastAPI(title="Delphi Engine", version="0.1.0")

    def get_state() -> AppContainer:
        """Return the app container.

        Returns:
            Wired collaborators.
        """
        return state

    def require_key(
        request: Request,
        deps: Annotated[AppContainer, Depends(get_state)],
    ) -> None:
        """Reject /v1 calls that do not present the configured API key.

        Args:
            request: Incoming HTTP request.
            deps: Container.

        """
        supplied = request.headers.get("x-api-key", "")
        expected = deps.api_key
        if (
            not expected
            or len(supplied) != len(expected)
            or not secrets.compare_digest(supplied, expected)
        ):
            raise HTTPException(status_code=401, detail="invalid API key")

    @app.post("/v1/works:batch-check", response_model=BatchCheckResponse)
    def batch_check(
        request: BatchCheckRequest,
        deps: Annotated[AppContainer, Depends(get_state)],
        _: Annotated[None, Depends(require_key)],
    ) -> BatchCheckResponse:
        """Exact identifier existence check.

        Args:
            request: Identities.
            deps: Container.

        Returns:
            Known/unknown rows.
        """
        return deps.catalog.batch_check(request)

    @app.get("/v1/works/{work_id}/neighborhood", response_model=Neighborhood)
    def get_neighborhood(
        work_id: UUID,
        mode: NeighborhoodMode,
        subcategory: str,
        deps: Annotated[AppContainer, Depends(get_state)],
        _: Annotated[None, Depends(require_key)],
        as_of: date | None = None,
        k: Annotated[int, Query(ge=1, le=50)] = 8,
    ) -> Neighborhood:
        """Return citation, content, or union neighbors.

        Args:
            work_id: Seed work.
            mode: Graph mode.
            subcategory: SYS-009 filter.
            deps: Container.
            as_of: Inclusive date bound.
            k: Content neighbor cap.

        Returns:
            Neighborhood.

        """
        try:
            return deps.catalog.neighborhood(work_id, mode, subcategory, as_of=as_of, k=k)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="work not found") from exc

    @app.post("/v1/uploads")
    async def post_upload(
        deps: Annotated[AppContainer, Depends(get_state)],
        _: Annotated[None, Depends(require_key)],
        file: Annotated[UploadFile, File()],
        consent_destination: Annotated[str, Form()],
        subcategory: Annotated[str, Form()],
    ) -> JSONResponse:
        """Accept a consented PDF and attach dual graphs.

        Args:
            deps: Container.
            file: PDF bytes.
            consent_destination: Must be delphi.
            subcategory: Content-graph filter.

        Returns:
            Extraction and union neighborhood.

        """
        payload = await _read_upload(file)
        try:
            extraction, neighborhood = upload_pdf(
                deps.catalog,
                payload,
                file.filename or "upload.pdf",
                consent_destination,
                subcategory,
                deps.extractor,
                deps.embedder,
            )
        except ConsentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except MissingDependencyError as extra:
            raise HTTPException(status_code=503, detail=str(extra)) from extra
        body = {
            "extraction": extraction.model_dump(mode="json"),
            "neighborhood": neighborhood.model_dump(mode="json"),
        }
        return JSONResponse(body)

    @app.get("/health")
    def health(deps: Annotated[AppContainer, Depends(get_state)]) -> dict[str, object]:
        """Liveness plus catalog size for Compose.

        Args:
            deps: Container.

        Returns:
            Status payload.
        """
        return {
            "status": "ok",
            "catalog": type(deps.catalog).__name__,
            "works": len(deps.catalog.list_works()),
        }

    @app.post("/v1/generate")
    def post_generate(
        request: PathRequest,
        deps: Annotated[AppContainer, Depends(get_state)],
        _: Annotated[None, Depends(require_key)],
    ) -> tuple[PathProposal, ...]:
        """Generate research_path or patent_whitespace proposals.

        Args:
            request: Kind, subcategory, and seed.
            deps: Container.

        Returns:
            Ranked proposals.

        """
        try:
            return generate_paths(deps.catalog, request, deps.generator)
        except ContextLeakError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="seed work not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except MissingDependencyError as extra:
            raise HTTPException(status_code=503, detail=str(extra)) from extra

    return app


async def _read_upload(file: UploadFile) -> bytes:
    """Read an upload, refusing bodies over the size cap.

    Args:
        file: Multipart PDF.

    Returns:
        Raw bytes.

    Raises:
        HTTPException: When the body exceeds the cap.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await file.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="PDF exceeds 25MB")
        chunks.append(block)
    return b"".join(chunks)
