"""
Monday.com API Client — full GraphQL v2 implementation.
Includes search, aggregate, and pipeline-health methods.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from config import MONDAY_API_TOKEN, MONDAY_API_VERSION, missing_setting_message

logger = logging.getLogger(__name__)


class MondayAPIError(Exception):
    """Raised when the Monday.com API returns an error or cannot be reached."""


class MondayAPIClient:
    """Client for interacting with the Monday.com GraphQL API v2."""

    BASE_URL = "https://api.monday.com/v2"

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_version: str = MONDAY_API_VERSION,
    ) -> None:
        self.api_token = (api_token or MONDAY_API_TOKEN).strip()
        self.api_version = api_version

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": self.api_version,
        }

    def _ensure_token(self) -> None:
        if not self.api_token:
            raise MondayAPIError(missing_setting_message("MONDAY_API_TOKEN"))

    def _execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query and return the `data` payload."""
        self._ensure_token()
        payload = {"query": query, "variables": variables or {}}
        try:
            resp = requests.post(
                self.BASE_URL, json=payload, headers=self.headers, timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            if "errors" in result:
                raise MondayAPIError(f"GraphQL Error: {result['errors']}")
            return result.get("data", {})
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response is not None else str(exc)
            raise MondayAPIError(f"HTTP Error: {body}") from exc
        except requests.exceptions.RequestException as exc:
            raise MondayAPIError(f"Request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Board listing
    # ------------------------------------------------------------------
    def get_all_boards(self) -> List[Dict[str, Any]]:
        """Return all boards (id, name, state, owner, columns, groups, items_count)."""
        query = """
        {
            boards(limit: 500) {
                id name description state
                owner { id email name }
                groups { id title }
                columns { id title type }
                items_count
                created_at updated_at
            }
        }
        """
        return self._execute_query(query).get("boards", [])

    def list_all_boards_summary(self) -> List[Dict[str, Any]]:
        """Lightweight board list — id, name, state, owner.name, items_count."""
        query = """
        {
            boards(limit: 500) {
                id name state items_count
                owner { name }
            }
        }
        """
        return self._execute_query(query).get("boards", [])

    # ------------------------------------------------------------------
    # Board detail
    # ------------------------------------------------------------------
    def get_board_by_id(self, board_id: int) -> Dict[str, Any]:
        query = """
        query GetBoard($id: [ID!]) {
            boards(ids: $id) {
                id name description state
                owner { id email name }
                groups { id title items_count }
                columns { id title type settings_str }
                items_count created_at updated_at
            }
        }
        """
        boards = self._execute_query(query, {"id": [str(board_id)]}).get("boards", [])
        return boards[0] if boards else {}

    def get_board_columns(self, board_id: int) -> List[Dict[str, Any]]:
        query = """
        query GetColumns($id: [ID!]) {
            boards(ids: $id) {
                columns { id title type settings_str archived }
            }
        }
        """
        boards = self._execute_query(query, {"id": [str(board_id)]}).get("boards", [])
        return boards[0].get("columns", []) if boards else []

    # ------------------------------------------------------------------
    # Items — get_board_items with pagination cursor support
    # ------------------------------------------------------------------
    def get_board_items(self, board_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch up to `limit` items from a board (single page)."""
        query = """
        query GetItems($id: [ID!], $limit: Int!) {
            boards(ids: $id) {
                items_page(limit: $limit) {
                    cursor
                    items {
                        id name created_at updated_at
                        column_values { id column { title } value text }
                    }
                }
            }
        }
        """
        boards = self._execute_query(query, {"id": [str(board_id)], "limit": limit}).get("boards", [])
        if boards:
            return boards[0].get("items_page", {}).get("items", [])
        return []

    # ------------------------------------------------------------------
    # Search items by keyword (text match across name + column values)
    # ------------------------------------------------------------------
    def search_items(
        self,
        board_id: int,
        query_text: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search within a board using Monday.com items_by_multiple_column_values
        or a client-side filter on get_board_items.
        """
        # Monday's GraphQL does not have a free-text search, so we fetch items
        # and filter client-side (fast for boards up to a few hundred items).
        items = self.get_board_items(board_id, limit=500)
        qt_lower = query_text.lower()
        matches = []
        for item in items:
            if qt_lower in (item.get("name") or "").lower():
                matches.append(item)
                continue
            for cv in item.get("column_values", []):
                if qt_lower in (cv.get("text") or "").lower() or \
                   qt_lower in (cv.get("value") or "").lower():
                    matches.append(item)
                    break
        return matches[:limit]

    # ------------------------------------------------------------------
    # Aggregate metric — count by status, sum by numbers column
    # ------------------------------------------------------------------
    def aggregate_metric(
        self,
        board_id: int,
        column_title: str,
        operation: str = "count_by_value",
    ) -> Dict[str, Any]:
        """
        Aggregate column data.

        Args:
            board_id:       Monday.com board ID
            column_title:   Human-readable column title (case-insensitive)
            operation:      'count_by_value' | 'sum' | 'avg' | 'min' | 'max'

        Returns:
            {
              "column": "<title>",
              "operation": "<op>",
              "result": <dict or number>,
              "item_count": <int>,
            }
        """
        items = self.get_board_items(board_id, limit=500)
        col_lower = column_title.lower().strip()

        values: List[Any] = []
        for item in items:
            for cv in item.get("column_values", []):
                title = cv.get("column", {}).get("title") or cv.get("id") or ""
                if title.lower().strip() == col_lower:
                    text = cv.get("text") or cv.get("value") or ""
                    values.append(text)
                    break

        if not values:
            return {
                "column": column_title,
                "operation": operation,
                "result": None,
                "item_count": len(items),
                "error": f"Column '{column_title}' not found or all values empty",
            }

        if operation == "count_by_value":
            counts: Dict[str, int] = {}
            for v in values:
                key = str(v).strip() or "Empty"
                counts[key] = counts.get(key, 0) + 1
            result: Any = dict(sorted(counts.items(), key=lambda x: -x[1]))

        elif operation in ("sum", "avg", "min", "max"):
            nums = []
            for v in values:
                try:
                    nums.append(float(str(v).replace(",", "")))
                except (ValueError, TypeError):
                    pass
            if not nums:
                result = None
            elif operation == "sum":
                result = round(sum(nums), 2)
            elif operation == "avg":
                result = round(sum(nums) / len(nums), 2)
            elif operation == "min":
                result = round(min(nums), 2)
            elif operation == "max":
                result = round(max(nums), 2)
        else:
            result = values

        return {
            "column": column_title,
            "operation": operation,
            "result": result,
            "item_count": len(items),
        }

    # ------------------------------------------------------------------
    # Pipeline health — group-level counts for CRM funnel boards
    # ------------------------------------------------------------------
    def get_pipeline_health(self, board_id: int) -> Dict[str, Any]:
        """
        Compute CRM-style pipeline health metrics for a board.

        Returns per-group item counts plus a deal-value sum if a
        numeric column containing 'value' or 'amount' or 'revenue' exists.
        """
        query = """
        query PipelineHealth($id: [ID!]) {
            boards(ids: $id) {
                name items_count
                groups { id title items_count }
                columns { id title type }
                items_page(limit: 500) {
                    items {
                        id name
                        group { id title }
                        column_values { id column { title } text value }
                    }
                }
            }
        }
        """
        boards = self._execute_query(query, {"id": [str(board_id)]}).get("boards", [])
        if not boards:
            return {"error": f"Board {board_id} not found"}

        board = boards[0]
        items = board.get("items_page", {}).get("items", [])
        groups = board.get("groups", [])
        columns = board.get("columns", [])

        # Find a value/amount/revenue numeric column
        value_col_id: Optional[str] = None
        for col in columns:
            title_lc = (col.get("title") or "").lower()
            if col.get("type") == "numbers" and any(
                kw in title_lc for kw in ("value", "amount", "revenue", "deal", "price")
            ):
                value_col_id = col.get("id")
                break

        # Group-level aggregation
        group_stats: Dict[str, Dict[str, Any]] = {
            g["id"]: {"name": g["title"], "count": 0, "total_value": 0.0}
            for g in groups
        }
        total_value = 0.0
        for item in items:
            gid = (item.get("group") or {}).get("id")
            if gid and gid in group_stats:
                group_stats[gid]["count"] += 1
            if value_col_id:
                for cv in item.get("column_values", []):
                    if cv.get("id") == value_col_id:
                        try:
                            v = float((cv.get("text") or "0").replace(",", ""))
                            if gid and gid in group_stats:
                                group_stats[gid]["total_value"] += v
                            total_value += v
                        except (ValueError, TypeError):
                            pass

        # Drop zero-value totals if no value column found
        stages = []
        for gdata in group_stats.values():
            entry: Dict[str, Any] = {
                "stage": gdata["name"],
                "count": gdata["count"],
            }
            if value_col_id:
                entry["total_value"] = round(gdata["total_value"], 2)
            stages.append(entry)

        result: Dict[str, Any] = {
            "board": board.get("name"),
            "total_items": board.get("items_count", 0),
            "pipeline_stages": stages,
        }
        if value_col_id:
            result["total_pipeline_value"] = round(total_value, 2)

        return result

    # ------------------------------------------------------------------
    # Create item
    # ------------------------------------------------------------------
    def create_item(
        self,
        board_id: int,
        group_id: str,
        item_name: str,
        column_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        query = """
        mutation CreateItem($board_id: ID!, $group_id: String!, $item_name: String!, $column_values: JSON) {
            create_item(board_id: $board_id, group_id: $group_id, item_name: $item_name, column_values: $column_values) {
                id name created_at
            }
        }
        """
        variables = {
            "board_id": str(board_id),
            "group_id": group_id,
            "item_name": item_name,
            "column_values": json.dumps(column_values or {}),
        }
        return self._execute_query(query, variables).get("create_item", {})
