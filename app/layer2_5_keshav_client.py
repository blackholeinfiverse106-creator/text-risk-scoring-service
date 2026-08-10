import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("sutradhara_control_plane")

def analyze_with_keshav(execution_id: str, trace_hash: str) -> Optional[Dict[str, Any]]:
    """
    Calls the external KESHAV analytics engine.
    
    Since KESHAV operates on dependency graphs (tasks/constraints) and 
    our project evaluates text-risk context signals, we use a Mock Adapter.
    We pass our trace continuity IDs into a mock dependency graph to successfully 
    traverse KESHAV's engine and extract a valid `keshav_output`.
    """
    keshav_url = os.environ.get("KESHAV_SERVICE_URL", "https://keshav-cia7.onrender.com")
    endpoint = f"{keshav_url}/analyze"
    
    # Mock task graph to satisfy the engine
    payload = {
        "trace_id": trace_hash,  # Ensure trace continuity with Sūtradhāra
        "execution_id": execution_id,
        "tasks": [{"task_id": "T1", "depends_on": []}],
        "constraint_results": [{"task_id": "T1", "is_valid": False, "unsatisfied_dependencies": []}],
        "propagation_results": [{"task_id": "T1", "affected_tasks": [], "impact_score": 10}]
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=15)
        if response.status_code == 200:
            keshav_output = response.json()
            logger.info(
                f"KESHAV Analysis Complete | root_cause={keshav_output.get('root_cause')} | severity={keshav_output.get('severity')}",
                extra={
                    "event_type": "keshav_analysis_success",
                    "trace_hash": trace_hash
                }
            )
            return keshav_output
        else:
            logger.warning(
                f"KESHAV API Failed | status={response.status_code} | response={response.text}",
                extra={"event_type": "keshav_analysis_failure"}
            )
            return None
    except Exception as e:
        logger.error(f"KESHAV Connection Error: {str(e)}")
        return None
