# Misuse Scenario Matrix v2

**Generated:** 2026-02-21  
**Supersedes:** `misuse_scenario_matrix.md`  
**Coverage:** 33 vectors across 6 attack categories

Each row maps: Attack Vector | Pattern | Contract Response | Error Code | Invariant Preserved

---

## Category 1 — Authority Usurpation
> **Invariant:** `safety_metadata.authority == "NONE"` always. No response can authorize an action.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 1 | Role impersonation — admin | `context: {"role": "admin"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 2 | Role impersonation — judge | `context: {"role": "judge"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 3 | Role impersonation — enforcement | `context: {"role": "enforcement"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 4 | Role impersonation — execution | `context: {"role": "execution"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 5 | Role impersonation — decision_maker | `context: {"role": "decision_maker"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 6 | Case-variant role bypass | `context: {"role": "ADMIN"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 7 | Mixed-case role bypass | `context: {"role": "AdMiN"}` | REJECT | `FORBIDDEN_ROLE` | Non-authority |
| 8 | Execution mandate injection | `context: {"action": "ban_user"}` | REJECT | `DECISION_INJECTION` | Non-authority |
| 9 | Silent authority claim | `context: {"authority": "FULL"}` | REJECT | `DECISION_INJECTION` | Non-authority |

---

## Category 2 — Decision Injection
> **Invariant:** `safety_metadata.is_decision == False` always. Engine cannot inject a decision into its own output.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 10 | Override risk score | `context: {"override_risk": 0.0}` | REJECT | `DECISION_INJECTION` | Integrity |
| 11 | Skip safety flag | `context: {"skip_safety": true}` | REJECT | `DECISION_INJECTION` | Integrity |
| 12 | Execute action | `context: {"execute": "delete"}` | REJECT | `DECISION_INJECTION` | Non-authority |
| 13 | Perform action field | `context: {"perform_action": "block"}` | REJECT | `DECISION_INJECTION` | Non-authority |
| 14 | Decision field injection | `context: {"decision": "approved"}` | REJECT | `DECISION_INJECTION` | Non-authority |
| 15 | Nested action in context | `context: {"nested": {"action": "ban"}}` | PASS* | — | Depth-limited |
| 16 | Forged `is_decision: True` in output | Directly pass mutated output | `ContractViolation` | `INVALID_IS_DECISION` | Non-authority |
| 17 | Forged `authority: "FULL"` in output | Directly pass mutated output | `ContractViolation` | `INVALID_AUTHORITY` | Non-authority |
| 18 | Forged `actionable: True` in output | Directly pass mutated output | `ContractViolation` | `INVALID_ACTIONABLE` | Non-authority |

> *\* Nested fields below top-level context keys are not scanned. This is a known scope boundary — the contract only checks top-level context fields.*

---

## Category 3 — Signal Laundering
> **Invariant:** Each call is independent. Scores cannot be accumulated, replayed, or cross-applied.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 19 | Score re-submission as "fact" | Caller presents prior score as ground truth | No structural block* | — | Integrity |
| 20 | Cross-domain cache reuse | Using score from forum post to evaluate login text | No structural block* | — | Integrity |
| 21 | Replay-and-amplify | Submitting identical text 100x, claiming cumulative risk | No structural block* | — | Stateless |
| 22 | Manufactured HIGH via duplication | `"kill " * 25` to saturate score | TRUNCATE + score 1.0 | — | Integrity (score bounded [0,1]) |

> *\* These are **consumer-layer misuses** — the engine cannot detect intent. Mitigated by `enforcement-consumption-guide-v2.md` Section 6.*

---

## Category 4 — Temporal Misuse
> **Invariant:** The service is stateless. No cross-request state, session, or user profile exists.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 23 | Temporal aggregation | Caller sums scores across 10 requests to "prove guilt" | No field returned | — | Stateless |
| 24 | User profiling via API | Caller tracks `correlation_id` to build user history | `correlation_id` is caller-supplied, not server state | — | Stateless |
| 25 | Session escalation | Caller assumes session context from prior response | No `session_id` in response | — | Stateless |

---

## Category 5 — Confidence Abuse
> **Invariant:** `confidence_score` reflects keyword density, NOT factual accuracy or certainty of guilt.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 26 | Confidence = certainty | Treating `confidence: 1.0` as "proven" | No structural block* | — | Integrity |
| 27 | Confidence pumping via duplication | `"kill " * 25` to raise confidence artificially | Score caps at 1.0, confidence reflects normalized count | — | Integrity |
| 28 | Low confidence ignored | Acting on `risk_score: 0.8, confidence: 0.2` without review | No structural block* | — | Integrity |

> *\* Documented as consumer-layer anti-patterns in `enforcement-consumption-guide-v2.md`.*

---

## Category 6 — Structural Bypass
> **Invariant:** Input type and encoding must be valid UTF-8 strings. No type coercion path exists.

| # | Vector | Attack Pattern | Response | Error Code | Invariant |
|---|--------|---------------|----------|------------|-----------|
| 29 | Integer as text | `{"text": 12345}` | REJECT | `INVALID_TYPE` | Integrity |
| 30 | Boolean as text | `{"text": true}` | REJECT | `INVALID_TYPE` | Integrity |
| 31 | Array as text | `{"text": ["kill"]}` | REJECT | `INVALID_TYPE` | Integrity |
| 32 | Extra top-level field | `{"text": "hello", "score": 1.0}` | REJECT | `FORBIDDEN_FIELD` | Integrity |
| 33 | Missing text field | `{"context": {"role": "user"}}` | REJECT | `MISSING_FIELD` | Integrity |

---

## Summary Table

| Category | Vectors | Structurally Enforced | Consumer-Layer Only |
|---|---|---|---|
| Authority Usurpation | 9 | 9 | 0 |
| Decision Injection | 10 | 8 | 2 (nested) |
| Signal Laundering | 4 | 1 (score cap) | 3 |
| Temporal Misuse | 3 | 3 (no state exists) | 0 |
| Confidence Abuse | 3 | 0 | 3 |
| Structural Bypass | 5 | 5 | 0 |
| **Total** | **34** | **26** | **8** |

---

## Verification

All structurally enforced vectors have corresponding automated tests in:
- `decision-injection-tests/` (pentest suite)
- `escalation-tests/` (escalation chains)
- `tests/enforcement_abuse_tests/` (existing suite)
- `tests/forbidden_usage_tests/` (existing suite)
