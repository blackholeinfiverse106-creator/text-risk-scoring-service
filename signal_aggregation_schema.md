# Unified Signal Schema for Aggregation

## 1. Supported Signal Types
The multi-signal aggregator accepts the following underlying signal types:
- **`TEXT_RISK_SIGNAL`**: Analyzed output from the core text engine.
- **`BEHAVIOR_ANOMALY_SIGNAL`**: Behavioral anomalies detected in the user session.
- **`POLICY_VIOLATION_SIGNAL`**: Hard policy breakages (e.g., TOS violations).
- **`EXTERNAL_DETECTOR_SIGNAL`**: Third-party or external heuristic outputs.

## 2. Unified Input Schema
Each signal input to the aggregator must adhere to the `UnifiedSignal` structure. To ensure DGIC compatibility, every signal is wrapped in a DGIC epistemic envelope.

```json
{
  "signal_id": "string (UUID or Hash)",
  "signal_type": "enum: TEXT_RISK_SIGNAL | BEHAVIOR_ANOMALY_SIGNAL | POLICY_VIOLATION_SIGNAL | EXTERNAL_DETECTOR_SIGNAL",
  "base_risk_score": "float [0.0, 1.0]",
  "base_confidence_score": "float [0.0, 1.0]",
  "dgic_envelope": {
    "version": "schema_v1",
    "lineage_hash": "string (SHA-256)",
    "envelope_hash": "string (SHA-256)",
    "payload": {
      "epistemic_state": "enum: KNOWN | INFERRED | AMBIGUOUS | UNKNOWN",
      "entropy_score": "float [0.0, 1.0]",
      "contradiction_flag": "boolean"
    },
    "collapse_flag": "boolean"
  }
}
```

## 3. Deterministic Weighting Rules

Each signal type has a deterministic base weight that influences how much it contributes to the final aggregated enforcement score.

| Signal Type                 | Base Weight ($W_t$) | Rationale                                |
|-----------------------------|---------------------|------------------------------------------|
| `POLICY_VIOLATION_SIGNAL`   | 1.5                 | Hard rules have highest priority.        |
| `BEHAVIOR_ANOMALY_SIGNAL`   | 1.2                 | Behavioral context strongly correlates with risk. |
| `TEXT_RISK_SIGNAL`          | 1.0                 | Standard textual analysis weight.        |
| `EXTERNAL_DETECTOR_SIGNAL`  | 0.8                 | Third-party signals are treated more cautiously. |

### Aggregation Algebra

1. **Effective Confidence ($C_{eff}$)**: The base confidence factored by the DGIC envelope's confidence multiplier (derived from `epistemic_state` and `entropy_score`).
2. **Effective Weight ($W_{eff}$)**: $W_t \times C_{eff}$
3. **Raw Aggregate Score**: 
   $$ \text{Score}_{raw} = \frac{\sum (Risk_i \times W_{eff,i})}{\sum W_{eff,i}} $$
   *(If sum of weights is 0, score is 0.0 or simple mean of unweighted active risks.)*
4. **Conflict Handling (Contradiction Penalty)**: Let $D$ be the contradiction density (number of contradicting signals divided by total signals). The aggregate score is scaled down deterministically:
   $$ \text{Score}_{penalised} = \text{Score}_{raw} \times (1.0 - D \times 0.5) $$
5. **Bounded Scoring**: The final score is tightly bounded to `[0.0, 1.0]`. If DGIC epistemic rules mandate a risk ceiling (e.g., `AMBIGUOUS` caps risk at `0.69`), the score is clamped accordingly.
6. **Confidence Propagation**: Aggregate confidence is the arithmetic mean of effective confidences of all non-abstained signals.

## 4. Output Contract
The aggregation strictly respects the existing `enforcement_output_contract_v4.json`. 
- `is_decision` = `false`
- `authority` = `"NONE"`
- `actionable` = `false`
- Output remains a unified signal. No enforcement execution occurs inside the aggregator.
