import sys
import json
import logging
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.layer3_dgic import EpistemicState, DGICInput, DGICPayload, compute_envelope_hash
from app.layer6_insightbridge import aggregate_signals
from app.layer6_insightbridge import map_to_insightbridge_contract

def main():
    logging.getLogger().setLevel(logging.CRITICAL)
    inp = sys.stdin.read()
    if not inp.strip():
        sys.exit(1)
        
    try:
        data = json.loads(inp)
    except json.JSONDecodeError:
        sys.exit(1)
        
    signals = []
    for item in data:
        text = item["text"]
        evidence = item["lineage_hash"]
        state = EpistemicState(item["state"])
        entropy = item["entropy"]
        contra = item["contra"]
        
        payload_obj = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contra)
        payload_dict = {
            "epistemic_state": state.value,
            "entropy_score": entropy,
            "contradiction_flag": contra
        }
        env_hash = compute_envelope_hash("schema_v1", evidence, payload_dict)
        
        dgic = DGICInput(
            version="schema_v1",
            lineage_hash=evidence,
            envelope_hash=env_hash,
            payload=payload_obj,
            collapse_flag=False
        )
        signals.append((text, dgic))
        
    if not signals:
        sys.exit(1)
        
    agg = aggregate_signals(signals)
    lineage_reference = signals[0][1].lineage_hash if signals else "none"
    ib_payload = map_to_insightbridge_contract(agg, lineage_reference)
    
    print(json.dumps(ib_payload))

if __name__ == "__main__":
    main()
