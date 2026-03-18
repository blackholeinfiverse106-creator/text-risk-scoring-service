# Enforcement Signal Traceability Specification
**Date:** 2026-03-09
**Status:** ✅ CERTIFIED
**Phase Tag:** `v-insightbridge-ready`

---

## 1. Objective
To guarantee unbroken cryptographic provenance from the initial intelligence processing (DGIC) through to the final safety-bounded enforcement payload sent to InsightBridge.

## 2. The Chain of Custody

The Text Risk Scoring Service must never break the chain of evidence. To ensure perfect auditability, the system implements a strict pass-through mechanism:

1. **DGIC Provenance (`lineage_hash`)**: 
   - The upstream intelligence core (DGIC) wraps its epistemic state (`UNKNOWN`, `AMBIGUOUS`, etc.) and the original text hash in a `schema_v1` envelope. This envelope contains a firmly validated `lineage_hash` (the SHA-256 fingerprint of the original data).
2. **Adapter Retention (`evidence_hash`)**: 
   - The strict `dgic_adapter.py` cryptographically seals the input. If the seal passes, the `lineage_hash` is extracted and preserved structurally as `evidence_hash` throughout internal pipeline memory.
3. **Aggregator Preservation**:
   - `enforcement_aggregator.py` requires all signals in a batch to share the SAME `evidence_hash`. If a batch tries to mix different evidence lineages, it throws an `AggregationContractViolation: HASH_MISMATCH`, preventing cross-contamination of isolated risk events.
4. **InsightBridge Emission (`epistemic_source_hash`)**:
   - The final output formatter (`insightbridge_adapter.py`) retrieves the preserved lineage hash and embeds it into the `enforcement_output_contract_v4.json` compliant payload under the strict key `epistemic_source_hash`.

## 3. The `enforcement_signal_id` Determinism
Additionally, the final emitted payload generates its own `enforcement_signal_id` by hashing a deterministic string containing:
`lineage_hash | risk_score | confidence | abstain_flag | contradiction_flag`

This proves not just *what* evidence was reviewed (`epistemic_source_hash`), but *exactly how* the system evaluated it (`enforcement_signal_id`).

## 4. Guarantee
InsightBridge is therefore mathematically guaranteed that the risk metrics it consumes are cryptographically bound to the exact, unmodified intelligence graph context evaluated by DGIC.
