from typing import Dict, Any
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

def map_to_insightbridge_contract(internal_result: Any, lineage_hash: str) -> Dict[str, Any]:
    """
    Deterministically transforms the internal enforcement payload into the strict
    InsightBridge v4 contract schema. 
    Guarantees 'decision' is null and 'authority' is 'NONE'.
    Guarantees mapping of ambiguous and abstained states.
    """
    
    # Handle both dict and object formats (like AggregatedSignal)
    if hasattr(internal_result, "aggregate_risk_score"):
        risk_score = getattr(internal_result, "aggregate_risk_score", 0.0)
        confidence = getattr(internal_result, "aggregate_confidence", 0.0)
        abstain_flag = getattr(internal_result, "all_abstained", False)
        contradiction_flag = getattr(internal_result, "contradiction_count", 0) > 0
    else:
        # Dictionary format
        risk_score = internal_result.get("risk_score", 0.0)
        confidence = internal_result.get("confidence_score", 0.0)
        
        # Metadata fields
        dgic_meta = internal_result.get("dgic_metadata", {})
        
        # Determine flags
        abstain_flag = False
        if "errors" in internal_result and internal_result["errors"].get("error_code") == "EPISTEMIC_ABSTENTION":
            abstain_flag = True
            
        contradiction_flag = dgic_meta.get("epistemic_warning", False) and dgic_meta.get("epistemic_state") == "AMBIGUOUS"
        
        # If the aggregator was used, contradiction_flag might also be mapped from "contradiction_penalty"
        if "aggregation_metadata" in internal_result:
            agg_meta = internal_result["aggregation_metadata"]
            if agg_meta.get("contradictions", 0) > 0:
                contradiction_flag = True

    if abstain_flag:
        risk_score = 0.0  # Force to 0.0 if abstaining
                
    # We must construct a deterministic signal ID. 
    # Use a hash of the original lineage hash and the risk result
    raw_for_id = f"{lineage_hash}|{risk_score}|{confidence}|{abstain_flag}|{contradiction_flag}"
    signal_id = hashlib.sha256(raw_for_id.encode("utf-8")).hexdigest()
    
    # The absolute invariant hardcodes
    decision = None
    authority = "NONE"
    
    output = {
        "enforcement_signal_id": signal_id,
        "epistemic_source_hash_chain": lineage_hash,
        "aggregated_risk_score": float(risk_score),
        "bounded_confidence": float(confidence),
        "contradiction_flag": contradiction_flag,
        "abstention_flag": abstain_flag,
        "decision": decision,
        "authority": authority
    }
    
    logger.debug("Mapped to InsightBridge contract", extra={"signal_id": signal_id})
    return output
