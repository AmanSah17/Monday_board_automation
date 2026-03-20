"""
Session manager — in-memory store for conversation history and extracted facts.
Interface is Redis-compatible so it can be swapped for a real Redis client later.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

# Maximum turns to keep in rolling window
_MAX_TURNS = 20
# Session TTL in seconds (2 hours)
_SESSION_TTL = 7200


class _SessionData:
    def __init__(self) -> None:
        self.history: List[Dict[str, str]] = []  # [{"role": "user"|"assistant", "content": "..."}]
        self.facts: Dict[str, Any] = {}          # entity-level extracted facts
        self.last_access: float = time.time()

    def touch(self) -> None:
        self.last_access = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_access) > _SESSION_TTL


class SessionStore:
    """Thread-safe in-memory session store."""

    def __init__(self) -> None:
        self._sessions: Dict[str, _SessionData] = defaultdict(_SessionData)

    def _get(self, session_id: str) -> _SessionData:
        sess = self._sessions[session_id]
        if sess.is_expired():
            self._sessions[session_id] = _SessionData()
        self._sessions[session_id].touch()
        return self._sessions[session_id]

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return last N turns of conversation history."""
        return self._get(session_id).history[-_MAX_TURNS:]

    def append_turn(self, session_id: str, user: str, assistant: str) -> None:
        """Append a completed user/assistant turn."""
        sess = self._get(session_id)
        sess.history.append({"role": "user", "content": user})
        sess.history.append({"role": "assistant", "content": assistant})

    def get_facts(self, session_id: str) -> Dict[str, Any]:
        """Return stored facts about this session (board IDs seen, preferences, etc.)"""
        return dict(self._get(session_id).facts)

    def set_facts(self, session_id: str, facts: Dict[str, Any]) -> None:
        """Merge new facts into the session."""
        self._get(session_id).facts.update(facts)

    def clear_session(self, session_id: str) -> None:
        """Reset a session (new conversation)."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


# Global singleton session store
session_store = SessionStore()
