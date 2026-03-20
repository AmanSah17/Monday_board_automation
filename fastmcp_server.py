"""
FastMCP server for monday.com board tools.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from monday_api_client import MondayAPIClient
from mcp.server.fastmcp import FastMCP



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

monday_client = MondayAPIClient()
mcp = FastMCP("monday-board-tools") if FastMCP is not None else None


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


if mcp is not None:

    @mcp.tool()
    def fetch_all_boards() -> Dict[str, Any]:
        """Fetch all monday.com boards accessible with the configured API token."""
        logger.info("MCP Tool: Fetching all boards")
        try:
            boards = monday_client.list_all_boards_summary()
            return {
                "success": True,
                "boards": boards,
                "total": len(boards),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error fetching boards: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def get_board_structure(board_id: int) -> Dict[str, Any]:
        """Get the structure of a monday.com board."""
        logger.info("MCP Tool: Getting structure for board %s", board_id)
        try:
            board = monday_client.get_board_by_id(board_id)
            columns = monday_client.get_board_columns(board_id)

            return {
                "success": True,
                "board_id": board_id,
                "board_name": board.get("name"),
                "columns": columns,
                "groups": board.get("groups", []),
                "description": board.get("description"),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error getting board structure: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def fetch_board_items(board_id: int, limit: int = 50) -> Dict[str, Any]:
        """Fetch items from a monday.com board with all column values."""
        logger.info("MCP Tool: Fetching items from board %s", board_id)
        try:
            items = monday_client.get_board_items(board_id, limit)
            board = monday_client.get_board_by_id(board_id)

            return {
                "success": True,
                "board_id": board_id,
                "board_name": board.get("name"),
                "items": items,
                "total": len(items),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error fetching board items: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def add_board_item(
        board_id: int,
        group_id: str,
        item_name: str,
        column_values: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a new item to a monday.com board."""
        logger.info("MCP Tool: Adding item '%s' to board %s", item_name, board_id)
        try:
            parsed_column_values = None
            if column_values:
                try:
                    parsed_column_values = json.loads(column_values)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Invalid JSON in column_values",
                        "timestamp": utc_now_iso(),
                    }

            item = monday_client.create_item(
                board_id,
                group_id,
                item_name,
                parsed_column_values,
            )

            return {
                "success": True,
                "board_id": board_id,
                "item": item,
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error adding board item: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def search_boards_by_name(search_term: str) -> Dict[str, Any]:
        """Search for monday.com boards by name."""
        logger.info("MCP Tool: Searching boards for term '%s'", search_term)
        try:
            all_boards = monday_client.list_all_boards_summary()

            matching_boards = [
                board
                for board in all_boards
                if search_term.lower() in board.get("name", "").lower()
            ]

            return {
                "success": True,
                "search_term": search_term,
                "matching_boards": matching_boards,
                "total": len(matching_boards),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error searching boards: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def get_board_summary(board_id: int) -> Dict[str, Any]:
        """Get a summary of a monday.com board including lightweight stats."""
        logger.info("MCP Tool: Getting summary for board %s", board_id)
        try:
            board = monday_client.get_board_by_id(board_id)
            columns = monday_client.get_board_columns(board_id)
            items = monday_client.get_board_items(board_id, limit=100)

            return {
                "success": True,
                "board_id": board_id,
                "board_name": board.get("name"),
                "description": board.get("description"),
                "owner": board.get("owner", {}),
                "state": board.get("state"),
                "total_items": board.get("items_count", 0),
                "total_columns": len(columns),
                "total_groups": len(board.get("groups", [])),
                "column_names": [column.get("title") for column in columns],
                "group_names": [group.get("title") for group in board.get("groups", [])],
                "recently_fetched_items": len(items),
                "created_at": board.get("created_at"),
                "updated_at": board.get("updated_at"),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error getting board summary: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.tool()
    def get_boards_list() -> Dict[str, Any]:
        """Get a formatted list of available boards."""
        logger.info("MCP Tool: Getting boards list")
        try:
            boards = monday_client.list_all_boards_summary()

            formatted_boards = [
                {
                    "id": board.get("id"),
                    "name": board.get("name"),
                    "owner": board.get("owner", {}).get("name"),
                    "state": board.get("state"),
                    "items_count": board.get("items_count", 0),
                }
                for board in boards
            ]

            return {
                "success": True,
                "boards": formatted_boards,
                "total_boards": len(boards),
                "timestamp": utc_now_iso(),
            }
        except Exception as e:
            logger.error("Error getting boards list: %s", e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": utc_now_iso(),
            }


    @mcp.resource("board://all")
    def get_all_boards_resource() -> str:
        """Resource for accessing all boards."""
        logger.info("MCP Resource: Accessing all boards")
        boards = monday_client.list_all_boards_summary()
        return json.dumps(boards, indent=2)


    @mcp.resource("board://{board_id}")
    def get_board_resource(board_id: int) -> str:
        """Resource for accessing a specific board."""
        logger.info("MCP Resource: Accessing board %s", board_id)
        board = monday_client.get_board_by_id(board_id)
        return json.dumps(board, indent=2)


if __name__ == "__main__":
    if mcp is None:
        raise SystemExit(
            "FastMCP is not installed in this environment. "
            "Install the 'mcp' package before running the MCP server."
        ) from MCP_IMPORT_ERROR

    import uvicorn

    logger.info("Starting FastMCP server for monday.com tools")
    uvicorn.run(mcp, host="0.0.0.0", port=9000)
