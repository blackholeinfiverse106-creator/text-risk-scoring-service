import re
import os

FILE_PATH = "c:\\blackhole\\text-risk-scoring-service\\chaos_harness.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update imports
import_old = """from app.dgic_adapter import (
    EpistemicState,
    DGICInput,
    DGICContractViolation,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    build_evidence_hash,
)"""

import_new = """from app.dgic_adapter import (
    EpistemicState,
    DGICInput,
    DGICPayload,
    DGICContractViolation,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    build_evidence_hash,
    compute_envelope_hash,
)"""

content = content.replace(import_old, import_new)

# 2. Add _make_dgic helper
helper_addition = """
_GOOD_EVIDENCE = build_evidence_hash("chaos_harness_benchmark")

def _make_dgic(state, entropy=0.0, contra=False, collapse=False, evidence=_GOOD_EVIDENCE, bad_hash=False):
    payload = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contra)
    payload_dict = {
        "epistemic_state": state.value if hasattr(state, "value") else state,
        "entropy_score": entropy,
        "contradiction_flag": contra
    }
    env_hash = compute_envelope_hash("schema_v1", evidence, payload_dict)
    if bad_hash:
        env_hash = "0" * 64
    return DGICInput(version="schema_v1", lineage_hash=evidence, envelope_hash=env_hash, payload=payload, collapse_flag=collapse)

def _make_raw_dgic(version, lineage, env_hash, payload, collapse):
    return DGICInput(version=version, lineage_hash=lineage, envelope_hash=env_hash, payload=payload, collapse_flag=collapse)
"""
content = content.replace("_GOOD_EVIDENCE = build_evidence_hash(\"chaos_harness_benchmark\")", helper_addition)


# We'll regex replace MALFORMED_CASES
malformed_cases_new = """MALFORMED_CASES: List[MalformedCase] = [
    # ── Envelope Corruption ──────────────────────────────
    MalformedCase(
        "bad_version", "envelope version is not schema_v1",
        lambda: validate_dgic_input(_make_raw_dgic("schema_v2", _GOOD_EVIDENCE, "0"*64, DGICPayload(EpistemicState.KNOWN, 0.0, False), False)),
        expect_exc=DGICContractViolation,
    ),
    MalformedCase(
        "bad_lineage_hash", "lineage_hash is not 64 chars",
        lambda: validate_dgic_input(_make_raw_dgic("schema_v1", "bad", "0"*64, DGICPayload(EpistemicState.KNOWN, 0.0, False), False)),
        expect_exc=DGICContractViolation,
    ),
    MalformedCase(
        "tampered_envelope_hash", "envelope hash does not match payload",
        lambda: validate_dgic_input(_make_dgic(EpistemicState.KNOWN, bad_hash=True)),
        expect_exc=DGICContractViolation,
    ),
    MalformedCase(
        "illegal_collapse", "ambiguous state with collapse_flag=True",
        lambda: validate_dgic_input(_make_dgic(EpistemicState.AMBIGUOUS, collapse=True)),
        expect_exc=DGICContractViolation,
    ),
    # ── Corrupted epistemic_state ──────────────────────────────
    MalformedCase(
        "corrupt_state_string", "epistemic_state is a raw string",
        lambda: validate_dgic_input(_make_raw_dgic("schema_v1", _GOOD_EVIDENCE, "0"*64, DGICPayload("FLYING", 0.0, False), False)),  # type: ignore
        expect_exc=DGICContractViolation,
    ),
    MalformedCase(
        "corrupt_state_none", "epistemic_state is None",
        lambda: validate_dgic_input(_make_raw_dgic("schema_v1", _GOOD_EVIDENCE, "0"*64, DGICPayload(None, 0.0, False), False)),  # type: ignore
        expect_exc=DGICContractViolation,
    ),
    # ── Type-confusion attacks ─────────────────────────────────
    MalformedCase(
        "contradiction_flag_int", "contradiction_flag is int 1",
        lambda: validate_dgic_input(_make_raw_dgic("schema_v1", _GOOD_EVIDENCE, "0"*64, DGICPayload(EpistemicState.KNOWN, 0.0, 1), False)), # type: ignore
        expect_exc=DGICContractViolation,
    ),
    # ── Non-DGICInput entirely ─────────────────────────────────
    MalformedCase(
        "plain_dict_instead_of_dgic", "Raw dict passed instead of DGICInput",
        lambda: validate_dgic_input({"epistemic_state": "KNOWN"}),
        expect_exc=DGICContractViolation,
    ),
    MalformedCase(
        "none_instead_of_dgic", "None passed as DGICInput",
        lambda: validate_dgic_input(None),   # type: ignore
        expect_exc=DGICContractViolation,
    ),
    # ── Aggregator-level malformed inputs ──────────────────────
    MalformedCase(
        "empty_signal_list", "aggregate_signals([]) — empty list",
        lambda: validate_aggregation_inputs([]),
        expect_exc=AggregationContractViolation,
    ),
    MalformedCase(
        "too_many_signals", "aggregate_signals with 33 signals",
        lambda: validate_aggregation_inputs([("text", _make_dgic(EpistemicState.KNOWN))] * 33),
        expect_exc=AggregationContractViolation,
    ),
    MalformedCase(
        "signal_not_tuple", "Signal element is a plain string",
        lambda: validate_aggregation_inputs(["not_a_tuple"]),  # type: ignore
        expect_exc=AggregationContractViolation,
    ),
    # ── Engine-level malformed text ────────────────────────────
    MalformedCase(
        "engine_none_input", "analyze_text(None)",
        lambda: analyze_text(None),   # type: ignore
        expect_exc=None,
        expect_error_key="INVALID_TYPE",
    ),
    MalformedCase(
        "engine_integer_input", "analyze_text(42)",
        lambda: analyze_text(42),     # type: ignore
        expect_exc=None,
        expect_error_key="INVALID_TYPE",
    ),
    MalformedCase(
        "engine_empty_after_strip", "analyze_text('   ')",
        lambda: analyze_text("   "),
        expect_exc=None,
        expect_error_key="EMPTY_INPUT",
    ),
    MalformedCase(
        "engine_huge_payload", "analyze_text(500k chars)",
        lambda: analyze_text("A" * 500_000),
        expect_exc=None,
        expect_error_key=None,
    ),
]"""

# Replace MALFORMED_CASES block
pattern = r"MALFORMED_CASES: List\[MalformedCase\] = \[\n.*?\]\n\n\ndef run_part_a"
content = re.sub(pattern, malformed_cases_new + "\n\n\ndef run_part_a", content, flags=re.DOTALL)


# 3. Update Part B (ENTROPY_CASES tests)
# Let's replace the section where dgic=DGICInput(...) is created in run_part_b
part_b_old = """            dgic = DGICInput(
                epistemic_state    = EpistemicState.INFERRED,
                entropy_score      = entropy_val,  # type: ignore
                contradiction_flag = False,
                collapse_flag      = False,
                evidence_hash      = _GOOD_EVIDENCE,
            )"""

part_b_new = """            
            # Since we purposely inject bad entropy values, we skip _make_dgic which auto-computes hashes based on values. 
            # We must provide a VALID hash for the bad value so it fails on the value itself, not the seal,
            # OR we just test validate_dgic_input directly on the payload structure.
            # wait, if entropy is bad, compute_envelope_hash will hash the bad value. 
            # If the value is a complex object, it will fail to hash. 
            # Let's do a try/except on hashing, and if it fails, just pass a dummy hash.
            try:
                payload_dict = {
                    "epistemic_state": "INFERRED",
                    "entropy_score": entropy_val,
                    "contradiction_flag": False
                }
                env_hash = compute_envelope_hash("schema_v1", _GOOD_EVIDENCE, payload_dict)
            except Exception:
                env_hash = "0" * 64
                
            payload = DGICPayload(epistemic_state=EpistemicState.INFERRED, entropy_score=entropy_val, contradiction_flag=False)
            dgic = DGICInput(
                version="schema_v1",
                lineage_hash=_GOOD_EVIDENCE,
                envelope_hash=env_hash,
                payload=payload,
                collapse_flag=False,
            )"""
            
content = content.replace(part_b_old, part_b_new)

# 4. Update Part C (_chaos_worker)
part_c_old = """    dgic = DGICInput(
        epistemic_state    = state,
        entropy_score      = entropy,
        contradiction_flag = contra,
        collapse_flag      = (thread_id % 7 == 0),
        evidence_hash      = build_evidence_hash(f"chaos:{thread_id}:{text[:20]}"),
    )"""

part_c_new = """    
    # Do not forcefully collapse AMBIGUOUS as it throws an error and we are testing invariants.
    # We will test illegal collapse in Part A (already added).
    collapse = (thread_id % 7 == 0) if state != EpistemicState.AMBIGUOUS else False
    dgic = _make_dgic(
        state, entropy, contra, collapse, 
        evidence=build_evidence_hash(f"chaos:{thread_id}:{text[:20]}")
    )"""
    
content = content.replace(part_c_old, part_c_new)

# 5. Update Part D (_build_ledger_entry & setup)
part_d_old = """        dgic = DGICInput(
            epistemic_state    = state,
            entropy_score      = entropy,
            contradiction_flag = contra,
            collapse_flag      = False,
            evidence_hash      = build_evidence_hash(f"ledger:{text[:30]}:{state.value}"),
        )"""

part_d_new = """        dgic = _make_dgic(
            state, entropy, contra, False,
            evidence=build_evidence_hash(f"ledger:{text[:30]}:{state.value}")
        )"""
content = content.replace(part_d_old, part_d_new)


with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated chaos_harness.py successfully.")
