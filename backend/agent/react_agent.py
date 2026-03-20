"""
ReAct agent with SSE streaming and LangSmith tracing.
Compatible with LangChain 1.0.x (create_agent / LangGraph-based).

Flow:
  1. Fast intent router (cheap LLM call, ~200ms)
  2. Full ReAct agent via create_agent (LangGraph) with 4 Monday.com tools
  3. Async generator emitting SSE-formatted trace events
"""
from __future__ import annotations

import json
import logging
import sys
import os
from typing import AsyncGenerator

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    ANTHROPIC_API_KEY,
    OPENAI_ROUTER_MODEL,
    OPENAI_REASONER_MODEL,
    LANGCHAIN_PROJECT,
    missing_setting_message,
)
from backend.agent.tools import BI_TOOLS
from backend.agent.prompts import BI_AGENT_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT
from backend.session import session_store

logger = logging.getLogger(__name__)


def _get_llm(model: str, streaming: bool = True):
    """Build a Chat Model instance based on the configured LLM_PROVIDER."""
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(missing_setting_message("ANTHROPIC_API_KEY"))
        return ChatAnthropic(
            model_name=model,
            temperature=0.0,
            api_key=api_key,
            streaming=streaming
        )
    else:
        # Default handles OpenAI, Groq, Ollama, vLLM, LMStudio via OPENAI_BASE_URL
        api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "not-needed")
        base_url = OPENAI_BASE_URL or os.getenv("OPENAI_BASE_URL", "")
        return ChatOpenAI(
            model=model,
            temperature=0.0,
            api_key=api_key,
            base_url=base_url if base_url else None,
            streaming=streaming
        )


# ---------------------------------------------------------------------------
# 1. Intent router — fast, cheap LLM call (~200ms)
# ---------------------------------------------------------------------------
@traceable(name="intent_router")
def classify_intent(query: str, history_summary: str = "") -> dict:
    """
    Classify user intent using the router LLM.
    Returns {intent, confidence, needs_clarification, clarification_question}.
    """
    llm = _get_llm(OPENAI_ROUTER_MODEL, streaming=False)
    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"Query: {query}\nContext: {history_summary}"),
    ]
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Strip markdown fences if model wraps in ```json ... ```
        if "```" in content:
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning("Router classification failed: %s", e)
        return {
            "intent": "other",
            "confidence": 0.5,
            "needs_clarification": False,
            "clarification_question": None,
        }


# ---------------------------------------------------------------------------
# 2. Build LangChain 1.x agent (LangGraph-backed)
# ---------------------------------------------------------------------------
def _build_agent(history_messages: list):
    """
    Build a LangChain 1.0.x create_agent graph with the BI tools.
    The system prompt is included in the message history.
    """
    llm = _get_llm(OPENAI_REASONER_MODEL, streaming=True)
    agent = create_agent(
        model=llm,
        tools=BI_TOOLS,
        system_prompt=BI_AGENT_SYSTEM_PROMPT,
        name="monday_bi_agent",
        debug=False,
    )
    return agent


# ---------------------------------------------------------------------------
# 3. SSE streaming runner
# ---------------------------------------------------------------------------
async def stream_agent_response(
    query: str,
    session_id: str = "default",
) -> AsyncGenerator[str, None]:
    """
    Async generator that runs the ReAct agent and yields SSE event strings.

    SSE event format (newline-delimited):
        data: {"type": "router",     "intent": "...", "confidence": 0.9}
        data: {"type": "token",      "content": "..."}
        data: {"type": "tool_start", "tool": "get_board", "input": {...}}
        data: {"type": "tool_end",   "tool": "get_board", "output": "..."}
        data: {"type": "done",       "answer": "..."}
        data: {"type": "error",      "message": "..."}
    """

    def _sse(event_dict: dict) -> str:
        return f"data: {json.dumps(event_dict, default=str)}\n\n"

    try:
        # 1. Session history
        history = session_store.get_history(session_id)
        history_summary = " | ".join(
            f"{t['role']}: {t['content'][:80]}" for t in history[-4:]
        )

        # 2. Router — fast intent classification
        router_result = classify_intent(query, history_summary)
        yield _sse({"type": "router", **router_result})

        # 3. Clarification short-circuit
        if router_result.get("needs_clarification") and router_result.get("clarification_question"):
            answer = router_result["clarification_question"]
            yield _sse({"type": "done", "answer": answer})
            session_store.append_turn(session_id, query, answer)
            return

        # 4. Build LangChain messages with history
        lc_messages = []
        for turn in history:
            if turn["role"] == "user":
                lc_messages.append(HumanMessage(content=turn["content"]))
            else:
                lc_messages.append(AIMessage(content=turn["content"]))
        lc_messages.append(HumanMessage(content=query))

        # 5. Build agent
        agent = _build_agent(lc_messages)

        # 6. Stream events using astream_events (LangChain 1.x)
        final_answer = ""
        input_payload = {"messages": lc_messages}

        async for event in agent.astream_events(input_payload, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            # Token-level streaming from LLM
            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk:
                    content = getattr(chunk, "content", "") or ""
                    if content:
                        yield _sse({"type": "token", "content": content})
                        final_answer += content

            # Tool start
            elif kind == "on_tool_start":
                tool_input = data.get("input", {})
                yield _sse({"type": "tool_start", "tool": name, "input": tool_input})

            # Tool end
            elif kind == "on_tool_end":
                tool_output = str(data.get("output", ""))
                yield _sse({
                    "type": "tool_end",
                    "tool": name,
                    "output": tool_output[:2000],
                })

            # Chain/agent end — capture final answer
            elif kind in ("on_chain_end", "on_agent_finish"):
                output = data.get("output")
                if isinstance(output, dict):
                    # LangGraph returns messages list in output
                    msgs = output.get("messages", [])
                    for msg in reversed(msgs):
                        if hasattr(msg, "content") and msg.content:
                            if not isinstance(msg, (HumanMessage,)):
                                final_answer = str(msg.content)
                                break
                elif isinstance(output, str) and output:
                    final_answer = output

        # 7. Emit done
        if not final_answer:
            final_answer = "The agent completed the analysis. Please check the trace panel for details."
        yield _sse({"type": "done", "answer": final_answer})

        # 8. Persist turn
        session_store.append_turn(session_id, query, final_answer)

    except Exception as e:
        logger.exception("Agent streaming error for session %s", session_id)
        yield _sse({"type": "error", "message": str(e)})
