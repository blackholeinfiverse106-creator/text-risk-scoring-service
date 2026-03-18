# Enforcement Consumption Guide

## 1. The Two-Key Rule (Golden Rule)
**NEVER allow the Text Risk Scoring Service to take an enforcement action alone.**

### ❌ Unsafe Pattern
`Input -> Risk Service -> Ban User`

### ✅ Safe Pattern
`Input -> Risk Service -> Policy Layer (Business Logic) -> Human Review (Optional) -> Enforcement Action`

## 2. Risk Score Interpretation
The `risk_score` is a heuristic signal (0.0 - 1.0). It is NOT a probability of guilt.

- **0.0 - 0.29 (LOW)**: Unlikely to violate policy. Safe to auto-approve (with audit log).
- **0.30 - 0.69 (MEDIUM)**: Ambiguous or potential risk. **Requires Human Review** or "Shadow ban" (hide visibility).
- **0.70 - 1.00 (HIGH)**: Strong keyword matches. **High priority for review**. Auto-action *only* if low-stakes (e.g., hold comment).

## 3. Circuit Breakers
If the service returns `503` or `TIMEOUT`, fail **SAFELY**:
- **Posting Content?** Allow with "Pending Review" flag.
- **Login?** Allow (don't block legitimate users due to risk service downtime).
- **Billing?** Allow.

**Do NOT fail closed (block everything) unless you are in a maximum-security context.**

## 4. Caching Policy
- **TTL**: Max 1 hour. Risk scores update as keywords evolve.
- **Key**: Hash of input text + current API version. 
- **Do NOT cache errors.**
