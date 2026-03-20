"""
LangChain tool definitions for the Monday.com BI Agent.
Each tool wraps the MondayAPIClient + normalizer pipeline.
"""
from __future__ import annotations

import json
import sys
import os
import logging
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain_core.tools import tool

from monday_api_client import MondayAPIClient, MondayAPIError
from backend.normalizer import normalize_board_data

logger = logging.getLogger(__name__)

# Shared client instance (token from env via config)
_monday = MondayAPIClient()


@tool
def get_board(board_id: int, limit: int = 100) -> str:
    """
    Get the structure and items of a Monday.com board.
    Returns board metadata (columns, groups) + normalized items.

    Args:
        board_id: The numeric Monday.com board ID.
        limit: Maximum number of items to fetch (1-500, default 100).
    """
    try:
        board = _monday.get_board_by_id(board_id)
        if not board:
            return json.dumps({"error": f"Board {board_id} not found"})

        items = _monday.get_board_items(board_id, limit=min(limit, 500))
        normalized = normalize_board_data(
            items,
            total_in_board=board.get("items_count"),
            limit_applied=limit,
        )

        return json.dumps({
            "board_id": board.get("id"),
            "board_name": board.get("name"),
            "description": board.get("description"),
            "state": board.get("state"),
            "owner": (board.get("owner") or {}).get("name"),
            "groups": [{"id": g["id"], "name": g["title"]} for g in board.get("groups", [])],
            "columns": [
                {"id": c["id"], "title": c["title"], "type": c["type"]}
                for c in board.get("columns", [])
            ],
            "total_item_count": board.get("items_count"),
            "items": normalized["items"],
            "fetched_count": normalized["count"],
            "caveat": normalized["caveat"],
        }, default=str)
    except MondayAPIError as e:
        logger.error("get_board tool error: %s", e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error in get_board")
        return json.dumps({"error": f"Unexpected error: {e}"})


@tool
def search_items(board_id: int, query: str, limit: int = 25) -> str:
    """
    Full-text search for items in a Monday.com board.
    Searches item names and all column values.

    Args:
        board_id: The numeric Monday.com board ID.
        query: Keyword or phrase to search for (case-insensitive).
        limit: Maximum number of matching items to return (default 25).
    """
    try:
        matches = _monday.search_items(board_id, query, limit=limit)
        normalized = normalize_board_data(matches, limit_applied=limit)
        return json.dumps({
            "board_id": board_id,
            "query": query,
            "matches": normalized["items"],
            "match_count": normalized["count"],
            "caveat": normalized["caveat"],
        }, default=str)
    except MondayAPIError as e:
        logger.error("search_items tool error: %s", e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error in search_items")
        return json.dumps({"error": f"Unexpected error: {e}"})


@tool
def aggregate_metric(
    board_id: int,
    column_title: str,
    operation: str = "count_by_value",
) -> str:
    """
    Aggregate data from a specific column in a Monday.com board.

    Args:
        board_id: The numeric Monday.com board ID.
        column_title: The exact column title to aggregate (case-insensitive).
        operation: One of:
            - 'count_by_value'  (default) — count items per distinct value/status
            - 'sum'             — sum all numeric values
            - 'avg'             — average of numeric values
            - 'min'             — minimum numeric value
            - 'max'             — maximum numeric value
    """
    try:
        result = _monday.aggregate_metric(board_id, column_title, operation)
        return json.dumps(result, default=str)
    except MondayAPIError as e:
        logger.error("aggregate_metric tool error: %s", e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error in aggregate_metric")
        return json.dumps({"error": f"Unexpected error: {e}"})


@tool
def get_pipeline_health(board_id: int) -> str:
    """
    Get CRM pipeline health metrics for a Monday.com board.
    Returns per-stage item counts and total deal values (if a numeric value column exists).
    Ideal for CRM, sales pipeline, deal funnel, or work-order boards.

    Args:
        board_id: The numeric Monday.com board ID.
    """
    try:
        result = _monday.get_pipeline_health(board_id)
        return json.dumps(result, default=str)
    except MondayAPIError as e:
        logger.error("get_pipeline_health tool error: %s", e)
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.exception("Unexpected error in get_pipeline_health")
        return json.dumps({"error": f"Unexpected error: {e}"})


# Exported tool list for the agent
BI_TOOLS = [get_board, search_items, aggregate_metric, get_pipeline_health]
