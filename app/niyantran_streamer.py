import threading
from collections import deque
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# In-memory store for recent execution states
_trace_history = deque(maxlen=200)
_trace_lock = threading.Lock()

def record_canonical_state(state: Dict[str, Any]):
    """
    Records the canonical execution state for the Niyantran Kendra dashboard.
    """
    with _trace_lock:
        _trace_history.appendleft(state)
    logger.debug(f"Niyantran Kendra state updated for execution_id={state.get('execution_id')}")

def get_recent_traces(limit: int = 50) -> List[Dict[str, Any]]:
    with _trace_lock:
        return list(_trace_history)[:limit]
