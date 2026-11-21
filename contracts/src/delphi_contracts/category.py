"""Category and subcategory filters."""

from typing import Annotated

from annotated_types import MinLen
from pydantic import BaseModel, ConfigDict

from delphi_contracts.enums import CategoryScheme, SubcategoryId

__all__ = ["Category", "CategoryScheme", "SubcategoryId"]


class Category(BaseModel):
    """One taxonomy node used as a generate/neighborhood filter.

    Attributes:
        scheme: openalex_topic or cpc.
        code: Scheme-native code.
        label: Human-readable name.
        subcategory: Prototype subcategory id when this node maps onto SYS-009.
        parent_code: Optional parent code in the same scheme.
    """

    model_config = ConfigDict(frozen=True)

    scheme: CategoryScheme
    code: Annotated[str, MinLen(1)]
    label: Annotated[str, MinLen(1)]
    subcategory: SubcategoryId | None = None
    parent_code: str | None = None
