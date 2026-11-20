"""SYS-009 ingest caps and computer-vision exclusions."""

from delphi_contracts.enums import SubcategoryId

__all__ = ["CapsError", "allowed_text", "check_caps"]

_CV_BLOCKLIST = ("medical imaging", "autonomous driving", "radiology")
_TRANSFORMERS = SubcategoryId.TRANSFORMERS_FOUNDATION_MODELS.value


class CapsError(ValueError):
    """Raised when transformers would exceed the other three subcategories."""


def allowed_text(text: str, subcategory: str) -> bool:
    """Return whether a record may enter the prototype slice.

    Args:
        text: Title plus abstract.
        subcategory: SYS-009 id.

    Returns:
        False for blocked computer-vision topics.
    """
    if subcategory != SubcategoryId.COMPUTER_VISION.value:
        return True
    blob = text.lower()
    return not any(term in blob for term in _CV_BLOCKLIST)


def check_caps(counts: dict[str, int]) -> None:
    """Reject a transformer-heavy ingest.

    Args:
        counts: Work counts by subcategory id.

    """
    transformers = counts.get(_TRANSFORMERS, 0)
    others = sum(value for key, value in counts.items() if key != _TRANSFORMERS)
    if transformers > others:
        raise CapsError("transformers slice exceeds the other three combined")
