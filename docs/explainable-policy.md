# Explainable Policy Updates

This document describes how every policy update in the
deterministic learning system is made explainable and auditable.

## Explanation Model

Every policy update answers four questions:

1. What changed?
2. Why did it change?
3. Which feedback triggered the change?
4. What constraints limited the update?

## Example Policy Update

- Affected category: fraud
- Previous weight: 0.50
- New weight: 0.55
- Reward signal: +1.0
- Triggering outcome: RISK_CONFIRMED
- Constraint applied: MAX_DELTA = 0.05

This ensures learning is incremental and bounded.

## Guarantee

No policy update can occur without a deterministic explanation.
