"""Catalog work records."""

from datetime import date
from typing import Annotated
from uuid import UUID

from annotated_types import MinLen
from pydantic import BaseModel, ConfigDict

from delphi_contracts.category import Category
from delphi_contracts.enums import WorkKind
from delphi_contracts.identity import Identity

__all__ = ["Work", "WorkKind"]


class Work(BaseModel):
    """A paper or patent in the catalog.

    Attributes:
        id: Stable internal UUID.
        kind: Paper or patent.
        title: Display title.
        authors: Ordered author or inventor names.
        keywords: Subject tokens when known (CPC/IPC for patents).
        abstract: Catalog abstract; may be empty for sparse records.
        claims: Independent or representative claim text when the source provides it.
        published_on: Publication or grant date used for hindcasting.
        identities: External identifiers.
        categories: Taxonomy assignments including subcategory.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    kind: WorkKind
    title: Annotated[str, MinLen(1)]
    authors: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    abstract: str = ""
    claims: tuple[str, ...] = ()
    published_on: date
    identities: tuple[Identity, ...] = ()
    categories: tuple[Category, ...] = ()
