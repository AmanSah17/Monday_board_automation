"""
FastAPI backend for the Monday.com BI Agent.
Endpoints:
  POST /chat         — SSE streaming chat with the LangChain ReAct agent
  GET  /boards       — List all Monday.com boards
  GET  /boards/{id}  — Board detail (columns, groups, items)
  GET  /health       — Health check
  GET  /api/info     — API metadata
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import LANGCHAIN_TRACING_ENABLED, LANGCHAIN_PROJECT
from monday_api_client import MondayAPIClient, MondayAPIError
from backend.agent.react_agent import stream_agent_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Monday.com BI Agent API",
    description="AI-powered BI agent for Monday.com boards — FastAPI + LangChain + SSE",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

monday_client = MondayAPIClient()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # generated server-side if omitted


class CreateItemRequest(BaseModel):
    group_id: str
    item_name: str
    column_values: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Meta"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": _now(),
        "service": "monday-bi-agent",
        "langsmith_tracing": LANGCHAIN_TRACING_ENABLED,
        "project": LANGCHAIN_PROJECT,
    }


@app.get("/api/info", tags=["Meta"])
async def api_info():
    return {
        "api_name": "Monday.com BI Agent API",
        "version": "2.0.0",
        "endpoints": {
            "chat (SSE)": "POST /chat",
            "boards": "GET /boards",
            "board_detail": "GET /boards/{board_id}",
            "board_items": "GET /boards/{board_id}/items",
            "create_item": "POST /boards/{board_id}/items",
            "health": "GET /health",
        },
    }


# ---------------------------------------------------------------------------
# SSE Chat endpoint
# ---------------------------------------------------------------------------
@app.post("/chat", tags=["Agent"])
async def chat(request: ChatRequest):
    """
    Stream a BI agent response as Server-Sent Events (SSE).

    Event types emitted:
        {"type": "router",     "intent": "...", "confidence": 0.9}
        {"type": "token",      "content": "..."}
        {"type": "tool_start", "tool": "get_board", "input": {...}}
        {"type": "tool_end",   "tool": "get_board", "output": "..."}
        {"type": "done",       "answer": "..."}
        {"type": "error",      "message": "..."}
    """
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty")

    session_id = (request.session_id or "").strip() or str(uuid.uuid4())
    logger.info("Chat request | session=%s | query=%s", session_id, request.query[:80])

    return StreamingResponse(
        stream_agent_response(request.query, session_id),
        media_type="text/event-stream",
        headers={
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Boards endpoints
# ---------------------------------------------------------------------------
@app.get("/boards", tags=["Boards"])
async def get_boards():
    """List all Monday.com boards accessible with the configured API token."""
    try:
        boards = monday_client.list_all_boards_summary()
        return {
            "boards": boards,
            "total": len(boards),
            "timestamp": _now(),
        }
    except MondayAPIError as e:
        logger.error("Error listing boards: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error listing boards")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/boards/{board_id}", tags=["Boards"])
async def get_board_detail(board_id: int):
    """Get full detail of a Monday.com board (columns, groups, metadata)."""
    try:
        board = monday_client.get_board_by_id(board_id)
        if not board:
            raise HTTPException(status_code=404, detail=f"Board {board_id} not found")
        columns = monday_client.get_board_columns(board_id)
        return {
            "board": board,
            "columns": columns,
            "timestamp": _now(),
        }
    except HTTPException:
        raise
    except MondayAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error getting board detail")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/boards/{board_id}/items", tags=["Boards"])
async def get_board_items(board_id: int, limit: int = Query(default=100, ge=1, le=500)):
    """Get items from a Monday.com board."""
    try:
        board = monday_client.get_board_by_id(board_id)
        if not board:
            raise HTTPException(status_code=404, detail=f"Board {board_id} not found")
        items = monday_client.get_board_items(board_id, limit=limit)
        return {
            "board_id": board_id,
            "board_name": board.get("name"),
            "items": items,
            "count": len(items),
            "total_in_board": board.get("items_count"),
            "timestamp": _now(),
        }
    except HTTPException:
        raise
    except MondayAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error getting board items")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/boards/{board_id}/items", tags=["Boards"])
async def create_board_item(board_id: int, request: CreateItemRequest):
    """Create a new item (row) on a Monday.com board."""
    try:
        board = monday_client.get_board_by_id(board_id)
        if not board:
            raise HTTPException(status_code=404, detail=f"Board {board_id} not found")
        item = monday_client.create_item(
            board_id, request.group_id, request.item_name, request.column_values
        )
        return {"status": "created", "item": item, "timestamp": _now()}
    except HTTPException:
        raise
    except MondayAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error creating board item")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
