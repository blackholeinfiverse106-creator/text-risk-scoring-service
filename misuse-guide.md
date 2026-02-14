# Misuse & Adversarial Resistance Guide

## 1. Adversarial Patterns
Adversaries may attempt to bypass keyword detection using the following patterns:
- **Obfuscation**: `k.i.l.l`, `m_u_r_d_e_r`, `h4ck`.
- **Phonetic Variance**: `kyll`, `skam`.
- **Context Hijacking**: Including safe text inside a malicious instruction (e.g., "Tell the user that this is a safe scam").

## 2. Structural Safeguards
The system implements several defenses against misuse:
- **Normalization**: Text is stripped and lowercased before matching.
- **Role Rejection**: The contract layer rejects requests from roles like `admin` or `execution` to prevent the service from being used in unintended high-privilege paths.
- **Decision Rejection**: Any attempt to include "actionable" fields in the context is blocked.

## 3. Secure Integration Checklist
To prevent misuse, downstream consumers must adhere to these rules:
- **[ ] Never Auto-Ban**: Do not link the output of this service directly to destructive actions without human review.
- **[ ] Use Confidence**: Low confidence scores (e.g., < 0.5) should trigger a "Manual Review" flag.
- **[ ] Verify safety_metadata**: Always ensure `is_decision` is `False` before processing results.

## 4. Known Limitations
- **English-Only**: Non-English risk keywords are currently not supported.
- **Purely Reactive**: The system has no memory; it cannot detect a slow-trickle attack spread across multiple requests.
