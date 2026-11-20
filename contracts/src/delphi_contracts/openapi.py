"""Canonical OpenAPI 3 document generated from Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse
from delphi_contracts.eval_run import EvalRun
from delphi_contracts.extraction import Extraction, PdfUpload
from delphi_contracts.neighborhood import Neighborhood
from delphi_contracts.paths import PathProposal, PathRequest
from delphi_contracts.work import Work

__all__ = ["build_openapi", "openapi_path", "write_openapi"]

_SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "Work": Work,
    "BatchCheckRequest": BatchCheckRequest,
    "BatchCheckResponse": BatchCheckResponse,
    "PdfUpload": PdfUpload,
    "Extraction": Extraction,
    "Neighborhood": Neighborhood,
    "PathRequest": PathRequest,
    "PathProposal": PathProposal,
    "EvalRun": EvalRun,
}


def openapi_path() -> Path:
    """Return the checked-in OpenAPI JSON path.

    Returns:
        Path to ``openapi.json`` beside this package.
    """
    return Path(__file__).with_name("openapi.json")


def build_openapi() -> dict[str, Any]:
    """Build an OpenAPI 3.1 document for the prototype REST surface.

    Returns:
        OpenAPI document as a JSON-serializable dict.
    """
    schemas = {name: model.model_json_schema() for name, model in _SCHEMA_MODELS.items()}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Delphi Engine",
            "version": "0.1.0",
            "description": "Prototype REST API owned by the contracts package.",
        },
        "paths": _paths(),
        "components": {"schemas": schemas},
    }


def write_openapi(path: Path | None = None) -> Path:
    """Write the OpenAPI document to disk.

    Args:
        path: Destination. Defaults to the package ``openapi.json``.

    Returns:
        Path written.
    """
    destination = path or openapi_path()
    destination.write_text(json.dumps(build_openapi(), indent=2) + "\n", encoding="utf-8")
    return destination


def _paths() -> dict[str, Any]:
    """Return prototype path items.

    Returns:
        OpenAPI paths object.
    """
    json_body = {"content": {"application/json": {"schema": {"type": "object"}}}}
    return {
        "/v1/works:batch-check": {
            "post": {
                "operationId": "batchCheckWorks",
                "summary": "Exact-identifier existence check",
                "requestBody": json_body,
                "responses": {"200": {"description": "Known/unknown rows"}},
            }
        },
        "/v1/works/{work_id}/neighborhood": {
            "get": {
                "operationId": "getNeighborhood",
                "summary": "Citation, content, or union neighborhood",
                "parameters": [
                    {
                        "name": "work_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "mode",
                        "in": "query",
                        "required": True,
                        "schema": {"enum": ["citation", "content", "union"]},
                    },
                ],
                "responses": {"200": {"description": "Dated neighbors tagged by edge kind"}},
            }
        },
        "/v1/uploads": {
            "post": {
                "operationId": "uploadPdf",
                "summary": "Consented PDF upload",
                "responses": {"200": {"description": "Extraction plus attached graphs"}},
            }
        },
        "/v1/generate": {
            "post": {
                "operationId": "generatePath",
                "summary": "Research path or patent whitespace from a masked neighborhood",
                "requestBody": json_body,
                "responses": {"200": {"description": "Ranked proposals"}},
            }
        },
    }
