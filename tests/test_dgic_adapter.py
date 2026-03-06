"""
Unit Tests: DGIC Adapter
========================
Tests every code path in app/dgic_adapter.py.

Coverage:
  - All 4 epistemic state paths via adapt_dgic()
  - Boundary values for entropy_score (0.0, 0.5, 1.0)
  - validate_dgic_input() rejection cases
  - apply_dgic_modifiers() for all scoring modes
  - Authority invariants across all paths
  - evidence_hash passthrough (never modified)
  - contradiction_flag / collapse_flag don't alter scoring
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.dgic_adapter import (
    EpistemicState,
    DGICInput,
    DGICAdapterResult,
    DGICContractViolation,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    build_evidence_hash,
    AMBIGUOUS_RISK_CEILING,
    AMBIGUOUS_CONFIDENCE_MULTIPLIER,
    INFERRED_ENTROPY_SCALING_FACTOR,
    ABSTENTION_ERROR_CODE,
)
from app.engine import analyze_text

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

EVIDENCE_HASH = "a" * 64  # 64-char mock hash

def make_dgic(
    state=EpistemicState.KNOWN,
    entropy=0.0,
    contradiction=False,
    collapse=False,
    evidence_hash=EVIDENCE_HASH,
):
    return DGICInput(
        epistemic_state=state,
        entropy_score=entropy,
        contradiction_flag=contradiction,
        collapse_flag=collapse,
        evidence_hash=evidence_hash,
    )

def high_risk_base():
    """A base engine result with HIGH risk (score=0.8)."""
    return {
        "risk_score": 0.8,
        "confidence_score": 0.9,
        "risk_category": "HIGH",
        "trigger_reasons": ["Detected violence keyword: kill"],
        "processed_length": 10,
        "safety_metadata": {
            "is_decision": False,
            "authority":   "NONE",
            "actionable":  False,
        },
        "errors": None,
    }

def low_risk_base():
    return {
        "risk_score": 0.2,
        "confidence_score": 1.0,
        "risk_category": "LOW",
        "trigger_reasons": [],
        "processed_length": 12,
        "safety_metadata": {
            "is_decision": False,
            "authority":   "NONE",
            "actionable":  False,
        },
        "errors": None,
    }


# ──────────────────────────────────────────────────────────────
# Part 1 — validate_dgic_input()
# ──────────────────────────────────────────────────────────────

class TestValidateDGICInput:

    def test_valid_input_does_not_raise(self):
        validate_dgic_input(make_dgic())

    def test_non_dgic_input_raises(self):
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input({"epistemic_state": "KNOWN"})
        assert exc.value.code == "INVALID_DGIC_TYPE"

    def test_invalid_epistemic_state_raises(self):
        bad = DGICInput(
            epistemic_state="FLYING",  # type: ignore
            entropy_score=0.0,
            contradiction_flag=False,
            collapse_flag=False,
            evidence_hash=EVIDENCE_HASH,
        )
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_EPISTEMIC_STATE"

    def test_entropy_bool_rejected(self):
        bad = DGICInput(
            epistemic_state=EpistemicState.KNOWN,
            entropy_score=True,  # bool is int subclass — must be rejected
            contradiction_flag=False,
            collapse_flag=False,
            evidence_hash=EVIDENCE_HASH,
        )
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_ENTROPY_TYPE"

    def test_entropy_below_zero_rejected(self):
        bad = make_dgic(entropy=-0.001)
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_ENTROPY_RANGE"

    def test_entropy_above_one_rejected(self):
        bad = make_dgic(entropy=1.001)
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_ENTROPY_RANGE"

    def test_entropy_boundary_values_accepted(self):
        validate_dgic_input(make_dgic(entropy=0.0))
        validate_dgic_input(make_dgic(entropy=1.0))
        validate_dgic_input(make_dgic(entropy=0.5))

    def test_contradiction_flag_non_bool_rejected(self):
        bad = DGICInput(
            epistemic_state=EpistemicState.KNOWN,
            entropy_score=0.0,
            contradiction_flag=1,  # int, not bool
            collapse_flag=False,
            evidence_hash=EVIDENCE_HASH,
        )
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_CONTRADICTION_FLAG"

    def test_collapse_flag_non_bool_rejected(self):
        bad = DGICInput(
            epistemic_state=EpistemicState.KNOWN,
            entropy_score=0.0,
            contradiction_flag=False,
            collapse_flag="yes",  # type: ignore
            evidence_hash=EVIDENCE_HASH,
        )
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_COLLAPSE_FLAG"

    def test_empty_evidence_hash_rejected(self):
        bad = make_dgic(evidence_hash="")
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_EVIDENCE_HASH"

    def test_whitespace_evidence_hash_rejected(self):
        bad = make_dgic(evidence_hash="   ")
        with pytest.raises(DGICContractViolation) as exc:
            validate_dgic_input(bad)
        assert exc.value.code == "INVALID_EVIDENCE_HASH"


# ──────────────────────────────────────────────────────────────
# Part 2 — adapt_dgic(): All 4 epistemic state paths
# ──────────────────────────────────────────────────────────────

class TestAdaptDGIC:

    def test_known_state_normal_mode(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.KNOWN))
        assert result.scoring_mode          == "NORMAL"
        assert result.confidence_multiplier == 1.0
        assert result.risk_ceiling          is None
        assert result.epistemic_warning     is False
        assert result.abstain               is False

    def test_inferred_entropy_zero(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=0.0))
        assert result.scoring_mode == "CONFIDENCE_SCALED"
        # 1.0 - 0.0 * 0.4 = 1.0
        assert result.confidence_multiplier == 1.0
        assert result.risk_ceiling          is None
        assert result.abstain               is False
        assert result.epistemic_warning     is False

    def test_inferred_entropy_half(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=0.5))
        expected = round(1.0 - 0.5 * INFERRED_ENTROPY_SCALING_FACTOR, 6)
        assert result.confidence_multiplier == expected
        assert result.scoring_mode == "CONFIDENCE_SCALED"

    def test_inferred_entropy_max(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=1.0))
        expected = round(1.0 - 1.0 * INFERRED_ENTROPY_SCALING_FACTOR, 6)
        assert result.confidence_multiplier == expected
        assert result.confidence_multiplier >= 0.0

    def test_ambiguous_state(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        assert result.scoring_mode          == "RISK_BOUNDED"
        assert result.risk_ceiling          == AMBIGUOUS_RISK_CEILING
        assert result.confidence_multiplier == AMBIGUOUS_CONFIDENCE_MULTIPLIER
        assert result.epistemic_warning     is True
        assert result.abstain               is False

    def test_unknown_state_abstains(self):
        result = adapt_dgic(make_dgic(state=EpistemicState.UNKNOWN))
        assert result.scoring_mode          == "ABSTAIN"
        assert result.abstain               is True
        assert result.epistemic_warning     is True
        assert result.risk_ceiling          == 0.0
        assert result.confidence_multiplier == 0.0

    def test_evidence_hash_passes_through_unmodified(self):
        my_hash = "deadbeef" * 8
        result = adapt_dgic(make_dgic(evidence_hash=my_hash))
        assert result.evidence_hash == my_hash

    def test_contradiction_flag_does_not_change_scoring_mode(self):
        r1 = adapt_dgic(make_dgic(state=EpistemicState.KNOWN, contradiction=False))
        r2 = adapt_dgic(make_dgic(state=EpistemicState.KNOWN, contradiction=True))
        assert r1.scoring_mode == r2.scoring_mode
        assert r1.confidence_multiplier == r2.confidence_multiplier
        assert r1.risk_ceiling == r2.risk_ceiling

    def test_collapse_flag_does_not_change_scoring_mode(self):
        r1 = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, collapse=False, entropy=0.5))
        r2 = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, collapse=True,  entropy=0.5))
        assert r1.scoring_mode           == r2.scoring_mode
        assert r1.confidence_multiplier  == r2.confidence_multiplier

    def test_collapse_flag_does_not_grant_authority(self):
        # collapse_flag=True must NEVER result in authority != NONE
        result = adapt_dgic(make_dgic(state=EpistemicState.KNOWN, collapse=True))
        # authority is checked in apply_dgic_modifiers, but adapter itself preserves boundary
        assert result.abstain is False  # collapse doesn't cause abstention
        assert result.scoring_mode == "NORMAL"


# ──────────────────────────────────────────────────────────────
# Part 3 — apply_dgic_modifiers(): Score transformation
# ──────────────────────────────────────────────────────────────

class TestApplyDGICModifiers:

    # --- NORMAL mode ---

    def test_normal_mode_does_not_modify_scores(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.KNOWN))
        base    = high_risk_base()
        result  = apply_dgic_modifiers(base, adapter)
        assert result["risk_score"]       == 0.8
        assert result["confidence_score"] == 0.9
        assert result["risk_category"]    == "HIGH"

    def test_normal_mode_adds_dgic_metadata(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.KNOWN))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert "dgic_metadata" in result
        assert result["dgic_metadata"]["scoring_mode"]      == "NORMAL"
        assert result["dgic_metadata"]["epistemic_state"]   == "KNOWN"
        assert result["dgic_metadata"]["epistemic_warning"] is False

    # --- CONFIDENCE_SCALED mode ---

    def test_confidence_scaled_half_entropy(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=0.5))
        base    = high_risk_base()  # confidence=0.9
        result  = apply_dgic_modifiers(base, adapter)
        expected = round(0.9 * adapter.confidence_multiplier, 2)
        assert result["confidence_score"] == expected
        assert result["risk_score"]       == 0.8   # risk score unchanged

    def test_confidence_scaled_zero_entropy(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=0.0))
        base    = high_risk_base()
        result  = apply_dgic_modifiers(base, adapter)
        assert result["confidence_score"] == 0.9   # multiplier=1.0, no change

    def test_confidence_cannot_exceed_one(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.INFERRED, entropy=0.0))
        base    = high_risk_base()
        base["confidence_score"] = 1.0
        result = apply_dgic_modifiers(base, adapter)
        assert result["confidence_score"] <= 1.0

    # --- RISK_BOUNDED mode ---

    def test_ambiguous_caps_high_score(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        base    = high_risk_base()  # risk_score=0.8 > ceiling 0.69
        result  = apply_dgic_modifiers(base, adapter)
        assert result["risk_score"]    <= AMBIGUOUS_RISK_CEILING
        assert result["risk_category"] != "HIGH"   # must be clamped below HIGH

    def test_ambiguous_does_not_raise_low_score(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        base    = low_risk_base()   # risk_score=0.2, already under ceiling
        result  = apply_dgic_modifiers(base, adapter)
        assert result["risk_score"] == 0.2     # not raised to ceiling

    def test_ambiguous_sets_epistemic_warning(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert result["dgic_metadata"]["epistemic_warning"] is True

    def test_ambiguous_halves_confidence(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        base    = high_risk_base()
        result  = apply_dgic_modifiers(base, adapter)
        expected = round(0.9 * AMBIGUOUS_CONFIDENCE_MULTIPLIER, 2)
        assert result["confidence_score"] == expected

    # --- ABSTAIN mode ---

    def test_unknown_returns_abstention(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.UNKNOWN))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert result["risk_score"]       == 0.0
        assert result["confidence_score"] == 0.0
        assert result["risk_category"]    == "LOW"
        assert result["trigger_reasons"]  == []

    def test_unknown_sets_abstention_error_code(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.UNKNOWN))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert result["errors"] is not None
        assert result["errors"]["error_code"] == ABSTENTION_ERROR_CODE

    def test_unknown_sets_epistemic_warning_in_metadata(self):
        adapter = adapt_dgic(make_dgic(state=EpistemicState.UNKNOWN))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert result["dgic_metadata"]["epistemic_warning"] is True

    # --- Authority invariants — ALL modes ---

    @pytest.mark.parametrize("state, entropy", [
        (EpistemicState.KNOWN,     0.0),
        (EpistemicState.INFERRED,  0.5),
        (EpistemicState.AMBIGUOUS, 0.0),
        (EpistemicState.UNKNOWN,   0.0),
    ])
    def test_safety_metadata_invariant_all_states(self, state, entropy):
        adapter = adapt_dgic(make_dgic(state=state, entropy=entropy))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        sm = result["safety_metadata"]
        assert sm["is_decision"] is False
        assert sm["authority"]   == "NONE"
        assert sm["actionable"]  is False

    # --- Evidence hash passthrough ---

    def test_evidence_hash_in_dgic_metadata_unmodified(self):
        my_hash = "cafebabe" * 8
        adapter = adapt_dgic(make_dgic(evidence_hash=my_hash))
        result  = apply_dgic_modifiers(high_risk_base(), adapter)
        assert result["dgic_metadata"]["evidence_hash"] == my_hash

    # --- Base result mutation guard ---

    def test_apply_modifiers_does_not_mutate_base(self):
        base       = high_risk_base()
        before     = base.copy()
        adapter    = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        apply_dgic_modifiers(base, adapter)
        # Original base should be unchanged
        assert base["risk_score"]    == before["risk_score"]
        assert base["risk_category"] == before["risk_category"]


# ──────────────────────────────────────────────────────────────
# Part 4 — Full Integration (engine + adapter)
# ──────────────────────────────────────────────────────────────

class TestEndToEndIntegration:

    def test_known_state_full_pipeline(self):
        text    = "kill and scam"
        base    = analyze_text(text)
        adapter = adapt_dgic(make_dgic(state=EpistemicState.KNOWN))
        result  = apply_dgic_modifiers(base, adapter)
        # Score should be unchanged by KNOWN
        assert result["risk_score"] == base["risk_score"]
        assert result["safety_metadata"]["authority"] == "NONE"

    def test_ambiguous_caps_engine_high_risk(self):
        text    = "kill attack bomb shoot murder"
        base    = analyze_text(text)
        adapter = adapt_dgic(make_dgic(state=EpistemicState.AMBIGUOUS))
        result  = apply_dgic_modifiers(base, adapter)
        # Engine score is HIGH; adapter must bound it
        if base["risk_score"] > AMBIGUOUS_RISK_CEILING:
            assert result["risk_score"] <= AMBIGUOUS_RISK_CEILING
            assert result["risk_category"] in ("LOW", "MEDIUM")

    def test_unknown_suppresses_high_risk(self):
        text    = "kill attack bomb"
        base    = analyze_text(text)
        assert base["risk_category"] in ("MEDIUM", "HIGH")  # confirm risky
        adapter = adapt_dgic(make_dgic(state=EpistemicState.UNKNOWN))
        result  = apply_dgic_modifiers(base, adapter)
        assert result["risk_score"]    == 0.0
        assert result["risk_category"] == "LOW"

    def test_build_evidence_hash_deterministic(self):
        h1 = build_evidence_hash("test input")
        h2 = build_evidence_hash("test input")
        assert h1 == h2

    def test_build_evidence_hash_different_inputs_differ(self):
        h1 = build_evidence_hash("input a")
        h2 = build_evidence_hash("input b")
        assert h1 != h2
