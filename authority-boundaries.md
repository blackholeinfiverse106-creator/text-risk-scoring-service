# Authority Boundaries - Text Risk Scoring Service

**Version**: 1.0.0  
**Status**: SEALED  
**Purpose**: Explicitly define what this system IS and what it IS NOT allowed to do.

---

## 1. The Core Axiom

> **"This system possesses ZERO execution authority. It provides SIGNALS, not DECISIONS."**

Any integration that treats the output of this service as a final decision violates the system's design contract and assumes all liability for resulting errors.

---

## 2. The 5 Pillars of Non-Authority

### Pillar I: No Decision Authority ❌
**Definition**: The system cannot authorize, deny, ban, delete, or approve anything.
**Constraint**: All outputs must be treated as *advisory input* to a separate decision-making layer (human or policy engine).
**Mechanism**: Every response includes `safety_metadata.is_decision = False`.

### Pillar II: No Semantic Understanding ❌
**Definition**: The system cannot understand intent, context, sarcasm, or nuance.
**Constraint**: Matches are strictly keyword-based. "I will kill time" is indistinguishable from "I will kill you" to this engine.
**Mechanism**: Documented limitation in `system-guarantees.md`.

### Pillar III: No Legal Standing ❌
**Definition**: The system cannot determine legality or compliance.
**Constraint**: Outputs must never be used as evidence of illegal activity or policy violation without human verification.
**Mechanism**: Explicit prohibition in `forbidden-usage.md`.

### Pillar IV: No Predictive Capability ❌
**Definition**: The system cannot predict future behavior or assess risk of future harm.
**Constraint**: Analysis is limited strictly to the *current text payload*.
**Mechanism**: Stateless design prevents historical profiling.

### Pillar V: No Agency ❌
**Definition**: The system cannot take action in the real world.
**Constraint**: API is read-only. It has no side effects (no database writes, no external calls).
**Mechanism**: Pure function architecture.

---

## 3. Boundary Definitions

### 3.1 The Execution Boundary
The line where risk signals stop and decisions begin.
- **INSIDE (Risk Service)**: Keyword detection, scoring, categorization.
- **OUTSIDE (Enforcement System)**: Policy application, thresholds, ban/allow decisions.

### 3.2 The Responsibility Boundary
The line where system reliability ends and user liability begins.
- **Service Responsibility**: Deterministic keyword matching.
- **User Responsibility**: Interpretation of results and actions taken.

---

## 4. Prohibited Domains (Absolute Exclusion)

Usage in these domains is **strictly forbidden** due to the inability of keyword matching to capture necessary complexity:

| Domain | Why Prohibited | Impact of Failure |
| :--- | :--- | :--- |
| **Medical / Psychological** | Diagnosis requires clinical context | Misdiagnosis, missed crisis |
| **Legal / Judicial** | Evidence requires chain of custody & intent | False conviction/acquittal |
| **Employment / HR** | Hiring requires holistic evaluation | Discrimination, unfair dismissal |
| **Credit / Financial** | Lending requires verified history | Financial exclusion |
| **Critical Infrastructure** | Safety requires physical guarantees | Physical harm, catastrophe |

---

## 5. Metadata Enforcement

Every response MUST contain the following immutable metadata block to reinforce these boundaries:

```json
"safety_metadata": {
  "is_decision": false,
  "authority": "NONE",
  "actionable": false
}
```

**Downstream Requirement**: Consumers MUST verify this block. If `is_decision` is ever `true` (impossible by design), the system must HALT.

---

**Authority Boundaries: SEALED ✓**
