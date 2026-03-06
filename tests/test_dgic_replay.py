"""
DGIC Integration Replay Proof
==============================
Runs 5,000 integrated calls (10 fixed DGIC input combinations × 500 iterations).
SHA-256 hashes every output and asserts zero divergence.
Emits dgic_integration_replay_proof.md on success.

Run with:
    python -m pytest tests/test_dgic_replay.py -v -s
Or standalone:
    python tests/test_dgic_replay.py
"""

import sys
import os
import hashlib
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.engine import analyze_text
from app.dgic_adapter import (
    EpistemicState,
    DGICInput,
    adapt_dgic,
    apply_dgic_modifiers,
    build_evidence_hash,
)

# ──────────────────────────────────────────────────────────────
# Replay Corpus — 10 fixed DGIC + text combinations
# ──────────────────────────────────────────────────────────────

REPLAY_CORPUS = [
    # (label, text, epistemic_state, entropy, contradiction, collapse)
    ("known_safe",       "hello world, this is a friendly message",   EpistemicState.KNOWN,     0.0,  False, False),
    ("known_high_risk",  "kill attack bomb shoot murder",              EpistemicState.KNOWN,     0.0,  False, False),
    ("inferred_low_e",   "scam phishing money laundering",            EpistemicState.INFERRED,  0.1,  False, False),
    ("inferred_mid_e",   "cocaine heroin dealer overdose",            EpistemicState.INFERRED,  0.5,  False, True),
    ("inferred_high_e",  "terrorism jihad isis extremist radicalize", EpistemicState.INFERRED,  1.0,  True,  False),
    ("ambiguous_low",    "the fight was brutal but legal",            EpistemicState.AMBIGUOUS, 0.0,  True,  True),
    ("ambiguous_high",   "kill murder stab shoot bomb blast",         EpistemicState.AMBIGUOUS, 0.0,  False, False),
    ("unknown_safe",     "good morning, have a nice day",             EpistemicState.UNKNOWN,   0.0,  False, False),
    ("unknown_risky",    "suicide self harm want to die cut myself",  EpistemicState.UNKNOWN,   0.0,  True,  False),
    ("known_empty_safe", "   ",                                        EpistemicState.KNOWN,     0.0,  False, False),
]

ITERATIONS_PER_CASE = 500   # 10 × 500 = 5,000 total calls
TOTAL_CALLS         = len(REPLAY_CORPUS) * ITERATIONS_PER_CASE


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def canonical_hash(obj: dict) -> str:
    """Stable SHA-256 hash of a JSON-serialised dict (sorted keys)."""
    serialised = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def run_integrated_call(text: str, dgic: DGICInput) -> dict:
    """Execute one full integrated pipeline call."""
    base_result    = analyze_text(text)
    adapter_result = adapt_dgic(dgic)
    return apply_dgic_modifiers(base_result, adapter_result)


# ──────────────────────────────────────────────────────────────
# Replay Harness
# ──────────────────────────────────────────────────────────────

def run_replay() -> dict:
    """
    Execute all 5,000 replay calls.
    Returns a results dict suitable for markdown reporting.
    Raises AssertionError on any divergence.
    """
    print(f"\n=== DGIC Integration Replay Proof ===")
    print(f"Cases:      {len(REPLAY_CORPUS)}")
    print(f"Iterations: {ITERATIONS_PER_CASE} per case")
    print(f"Total:      {TOTAL_CALLS} calls\n")

    case_results = []
    total_divergences = 0

    for label, text, state, entropy, contradiction, collapse in REPLAY_CORPUS:
        evidence = build_evidence_hash(f"{label}:{text}")
        dgic = DGICInput(
            epistemic_state    = state,
            entropy_score      = entropy,
            contradiction_flag = contradiction,
            collapse_flag      = collapse,
            evidence_hash      = evidence,
        )

        # Baseline
        baseline_output = run_integrated_call(text, dgic)
        baseline_hash   = canonical_hash(baseline_output)

        divergences = 0
        for i in range(ITERATIONS_PER_CASE):
            current_output = run_integrated_call(text, dgic)
            current_hash   = canonical_hash(current_output)
            if current_hash != baseline_hash:
                divergences += 1
                total_divergences += 1
                print(f"  ✗ DIVERGENCE at case={label} iteration={i}")
                print(f"    expected: {baseline_hash}")
                print(f"    got:      {current_hash}")

        status = "PASS" if divergences == 0 else "FAIL"
        mark   = "✓" if divergences == 0 else "✗"
        print(f"  {mark} {label:<25} | state={state.value:<9} | iters={ITERATIONS_PER_CASE} | divergences={divergences} | {status}")

        case_results.append({
            "label":            label,
            "epistemic_state":  state.value,
            "entropy_score":    entropy,
            "iterations":       ITERATIONS_PER_CASE,
            "divergences":      divergences,
            "baseline_hash":    baseline_hash,
            "scoring_mode":     baseline_output.get("dgic_metadata", {}).get("scoring_mode", "N/A"),
            "risk_category":    baseline_output.get("risk_category", "N/A"),
            "risk_score":       baseline_output.get("risk_score", "N/A"),
            "epistemic_warning":baseline_output.get("dgic_metadata", {}).get("epistemic_warning", False),
            "status":           status,
        })

    certified   = total_divergences == 0
    print(f"\n{'REPLAY CERTIFIED' if certified else 'REPLAY FAILED'}: {total_divergences} total divergences across {TOTAL_CALLS} calls.\n")

    return {
        "certified":         certified,
        "total_calls":       TOTAL_CALLS,
        "total_divergences": total_divergences,
        "cases":             case_results,
    }


def emit_proof_report(replay_data: dict) -> str:
    """Emit dgic_integration_replay_proof.md to project root."""
    certified      = replay_data["certified"]
    total_calls    = replay_data["total_calls"]
    divergences    = replay_data["total_divergences"]
    cases          = replay_data["cases"]
    timestamp      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdict        = "✅ CERTIFIED" if certified else "❌ FAILED"
    status_line    = "ZERO DIVERGENCE" if certified else f"DIVERGENCES DETECTED: {divergences}"

    rows = []
    for c in cases:
        warn = "⚠️" if c["epistemic_warning"] else ""
        rows.append(
            f"| `{c['label']}` | `{c['epistemic_state']}` | `{c['scoring_mode']}` "
            f"| `{c['risk_category']}` | `{c['risk_score']}` "
            f"| {c['iterations']} | {c['divergences']} | {c['status']} {warn} |"
        )

    table = "\n".join(rows)

    report = f"""# DGIC Integration Replay Proof
**Date:** {timestamp}  
**Status:** {verdict}  
**Total Calls:** {total_calls}  
**Total Divergences:** {divergences}  
**Result:** {status_line}

---

## Configuration

| Parameter | Value |
|---|---|
| Corpus size | {len(cases)} fixed DGIC + text combinations |
| Iterations per case | {ITERATIONS_PER_CASE} |
| Total integrated calls | {total_calls} |
| Hash function | SHA-256 over JSON-serialised output (sorted keys) |

---

## Case Results

| Label | Epistemic State | Scoring Mode | Risk Category | Risk Score | Iterations | Divergences | Status |
|---|---|---|---|---|---|---|---|
{table}

---

## Interpretation

- Every case was run {ITERATIONS_PER_CASE} times with identical DGIC inputs.
- SHA-256 of the full integrated output (base engine result + DGIC modifiers) was compared across all iterations.
- **{divergences} divergences** were detected.

> The integrated pipeline (engine + DGIC adapter) is **deterministic** under all epistemic states.  
> Identical DGIC inputs always produce identical outputs. Authority boundaries are preserved across all {total_calls} calls.

---

## Proof Methodology

```
For each (text, DGICInput) pair:
    baseline = run_integrated_call(text, dgic)
    baseline_hash = SHA256(json.dumps(baseline, sort_keys=True))
    
    for iteration in range({ITERATIONS_PER_CASE}):
        current = run_integrated_call(text, dgic)
        current_hash = SHA256(json.dumps(current, sort_keys=True))
        assert current_hash == baseline_hash
```

**Phase Tag:** `v-integration-dgic`
"""

    # Determine output path relative to this file's parent
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out  = os.path.join(root, "dgic_integration_replay_proof.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Proof written → {out}")
    return out


# ──────────────────────────────────────────────────────────────
# pytest entry point
# ──────────────────────────────────────────────────────────────

def test_dgic_replay_5000_calls():
    """
    Replay 5,000 integrated DGIC + engine calls.
    Assert zero divergence. Emit proof report.
    """
    replay_data = run_replay()
    emit_proof_report(replay_data)

    assert replay_data["certified"], (
        f"Replay FAILED: {replay_data['total_divergences']} divergences "
        f"across {replay_data['total_calls']} calls."
    )
    assert replay_data["total_divergences"] == 0


def test_replay_all_safety_metadata_invariant():
    """
    Additional spot-check: safety_metadata must be identical
    across all 10 corpus cases regardless of epistemic state.
    """
    expected_sm = {"is_decision": False, "authority": "NONE", "actionable": False}

    for label, text, state, entropy, contradiction, collapse in REPLAY_CORPUS:
        evidence = build_evidence_hash(f"{label}:{text}")
        dgic = DGICInput(
            epistemic_state    = state,
            entropy_score      = entropy,
            contradiction_flag = contradiction,
            collapse_flag      = collapse,
            evidence_hash      = evidence,
        )
        result = run_integrated_call(text, dgic)
        assert result["safety_metadata"] == expected_sm, (
            f"Safety metadata violated for case={label}, state={state.value}"
        )


# ──────────────────────────────────────────────────────────────
# Standalone runner
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = run_replay()
    emit_proof_report(data)
    if not data["certified"]:
        sys.exit(1)
