# Deterministic Learning Loop

This document describes how the system updates policy
parameters using deterministic, rule-based feedback.

## Learning Process

1. Risk engine produces a risk_category
2. External feedback provides outcome signal
3. Reward is calculated deterministically
4. Policy parameters are updated with bounded rules
5. A new immutable policy version is produced

## Guarantees

- No randomness is used
- Policy updates are bounded
- Past states are never mutated
- Replay produces identical results
