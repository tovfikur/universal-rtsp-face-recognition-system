"""
Stream State Manager - Persist and restore active stream state.
"""

import json
from pathlib import Path
from threading import RLock
from typing import Optional, Dict


class StreamStateManager:
    """Manage persistent stream state across restarts."""

    def __init__(self, state_file: Path):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        # Load existing state
        self._state = self._load_state()
        print(f"[StreamState] Initialized at {self.state_file}")
        if self._state.get("active"):
            print(f"[StreamState] Found active stream: {self._state.get('source')}")

    def _load_state(self) -> Dict:
        """Load state from file."""
        if not self.state_file.exists():
            return {"active": False, "source": None}

        try:
            with self.state_file.open("r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[StreamState] Error loading state: {e}")
            return {"active": False, "source": None}

    def _save_state(self):
        """Save state to file."""
        try:
            with self.state_file.open("w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            print(f"[StreamState] Error saving state: {e}")

    def set_active(self, source: str, source_type: str = "unknown"):
        """Mark stream as active."""
        with self._lock:
            self._state = {
                "active": True,
                "source": source,
                "source_type": source_type
            }
            self._save_state()
            print(f"[StreamState] Stream activated: {source}")

    def set_inactive(self):
        """Mark stream as inactive."""
        with self._lock:
            self._state = {
                "active": False,
                "source": self._state.get("source"),
                "source_type": self._state.get("source_type")
            }
            self._save_state()
            print(f"[StreamState] Stream deactivated")

    def is_active(self) -> bool:
        """Check if stream should be active."""
        with self._lock:
            return self._state.get("active", False)

    def get_source(self) -> Optional[str]:
        """Get the active source."""
        with self._lock:
            return self._state.get("source")

    def get_state(self) -> Dict:
        """Get full state."""
        with self._lock:
            return self._state.copy()
