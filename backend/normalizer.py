"""
Data normalizer for Monday.com board data.
Runs before the LLM sees any data: handles nulls, maps statuses to
canonical labels, coerces types, and attaches caveat notes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Status label mappings — extend as needed for your boards
# ------------------------------------------------------------------
_STATUS_CANONICAL: Dict[str, str] = {
    # CRM pipeline stages
    "new lead": "New Lead",
    "in contact": "In Contact",
    "qualified": "Qualified",
    "proposal sent": "Proposal Sent",
    "negotiation": "Negotiation",
    "closed won": "Closed Won",
    "closed lost": "Closed Lost",
    # Work orders
    "not started": "Not Started",
    "in progress": "In Progress",
    "done": "Done",
    "stuck": "Stuck",
    "on hold": "On Hold",
    # Generic
    "active": "Active",
    "paused": "Paused",
    "cancelled": "Cancelled",
}


def _canonical_status(raw: Optional[str]) -> str:
    """Map a raw status label to a canonical form."""
    if not raw:
        return "Unknown"
    return _STATUS_CANONICAL.get(raw.lower().strip(), raw.strip())


def _coerce_value(raw_value: Optional[str], col_type: str) -> Any:
    """Coerce a raw string value to the appropriate Python type."""
    if raw_value is None or raw_value == "" or raw_value == "null":
        return None
    if col_type in ("numbers", "numeric"):
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return None
    if col_type in ("date", "timeline"):
        return raw_value  # keep ISO string
    if col_type == "checkbox":
        return raw_value.lower() in ("true", "1", "yes", "v")
    return raw_value  # text / status / dropdown — keep as string


def normalize_column_value(col: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single column-value object from the Monday.com API."""
    col_type = (col.get("type") or "text").lower()
    raw_text = col.get("text")
    raw_value = col.get("value")

    if col_type == "status":
        display = _canonical_status(raw_text)
    else:
        display = _coerce_value(raw_text, col_type) if raw_text is not None else \
                  _coerce_value(raw_value, col_type)

    title = col.get("column", {}).get("title") or col.get("id")
    
    return {
        "id": col.get("id"),
        "title": title,
        "type": col_type,
        "value": display,
    }


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single board item."""
    columns = [
        normalize_column_value(cv)
        for cv in (item.get("column_values") or [])
        if cv.get("id") not in ("__last_updated__",)  # skip internal cols
    ]
    # Filter out fully-null columns to keep context compact
    non_null_cols = [c for c in columns if c["value"] is not None]
    null_count = len(columns) - len(non_null_cols)

    result: Dict[str, Any] = {
        "id": item.get("id"),
        "name": item.get("name"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "columns": non_null_cols,
    }
    if null_count > 0:
        result["_null_columns_omitted"] = null_count
    return result


def normalize_board_data(
    raw_items: List[Dict[str, Any]],
    *,
    total_in_board: Optional[int] = None,
    limit_applied: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Normalize a list of raw Monday.com items into a clean, LLM-ready dict.

    Returns:
        {
          "items": [...normalized items...],
          "count": <int>,
          "caveat": "<N of M items shown. ...>" or None,
        }
    """
    normalized = [normalize_item(item) for item in raw_items]
    n = len(normalized)
    total = total_in_board or n

    caveat: Optional[str] = None
    if limit_applied and n < total:
        caveat = (
            f"Showing {n} of {total} items (limit={limit_applied}). "
            "Ask for more items or apply a filter to see the rest."
        )

    return {
        "items": normalized,
        "count": n,
        "caveat": caveat,
    }
