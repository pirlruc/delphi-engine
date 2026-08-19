"""Category and subcategory filters."""

from pydantic import BaseModel, ConfigDict, Field

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
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    subcategory: SubcategoryId | None = None
    parent_code: str | None = None
