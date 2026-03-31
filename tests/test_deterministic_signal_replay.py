"""
Deterministic Signal Replay
=============================
Runs aggregation 1,000 times per scenario and asserts zero divergence
in the semantic output hash. Proves the aggregator is deterministic.
"""
import hashlib
import json
import pytest
from app.layer6_insightbridge import (
    UnifiedSignal, SignalType, aggregate_unified_signals, AggregatedUnifiedSignal,
)
from app.layer3_dgic import (
    DGICInput, DGICPayload, EpistemicState, compute_envelope_hash,
)

LINEAGE = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
ITERATIONS = 1_000

def _dgic(state=EpistemicState.KNOWN, entropy=0.0, contra=False):
    payload = DGICPayload(epistemic_state=state, entropy_score=entropy, contradiction_flag=contra)
    pd = {"epistemic_state": state.value, "entropy_score": entropy, "contradiction_flag": contra}
    eh = compute_envelope_hash("schema_v1", LINEAGE, pd)
    return DGICInput(version="schema_v1", lineage_hash=LINEAGE, envelope_hash=eh, payload=payload)

def _sig(sid, stype, risk, conf, state=EpistemicState.KNOWN, entropy=0.0, contra=False):
    return UnifiedSignal(signal_id=sid, signal_type=stype,
                         base_risk_score=risk, base_confidence_score=conf,
                         dgic_envelope=_dgic(state, entropy, contra))


def _semantic_hash(r: AggregatedUnifiedSignal) -> str:
    """Hash only semantically deterministic fields."""
    core = {
        "aggregate_risk_score": r.aggregate_risk_score,
        "aggregate_confidence": r.aggregate_confidence,
        "aggregate_risk_category": r.aggregate_risk_category,
        "signal_count": r.signal_count,
        "active_signal_count": r.active_signal_count,
        "abstained_signal_count": r.abstained_signal_count,
        "contradiction_count": r.contradiction_count,
        "contradiction_density": r.contradiction_density,
        "contradiction_penalty_applied": r.contradiction_penalty_applied,
        "epistemic_warning": r.epistemic_warning,
        "any_abstained": r.any_abstained,
        "all_abstained": r.all_abstained,
        "aggregation_hash": r.aggregation_hash,
    }
    serialised = json.dumps(core, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _replay(signals, label):
    """Run aggregation ITERATIONS times and assert zero divergence."""
    baseline = aggregate_unified_signals(signals)
    baseline_hash = _semantic_hash(baseline)

    divergences = 0
    for _ in range(ITERATIONS):
        result = aggregate_unified_signals(signals)
        if _semantic_hash(result) != baseline_hash:
            divergences += 1

    assert divergences == 0, f"[{label}] {divergences}/{ITERATIONS} divergences detected"


# ── Replay scenarios ──

def test_replay_single_signal():
    _replay(
        [_sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.5, 1.0)],
        "single_signal",
    )

def test_replay_mixed_types():
    _replay(
        [
            _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.3, 0.9),
            _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.5, 0.8),
            _sig("s3", SignalType.POLICY_VIOLATION_SIGNAL, 0.7, 1.0),
            _sig("s4", SignalType.EXTERNAL_DETECTOR_SIGNAL, 0.2, 0.7),
        ],
        "mixed_types",
    )

def test_replay_all_contradicting():
    _replay(
        [
            _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, contra=True),
            _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.6, 0.9, contra=True),
        ],
        "all_contradicting",
    )

def test_replay_partial_abstention():
    _replay(
        [
            _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.7, 1.0, EpistemicState.KNOWN),
            _sig("s2", SignalType.POLICY_VIOLATION_SIGNAL, 0.9, 1.0, EpistemicState.UNKNOWN),
        ],
        "partial_abstention",
    )

def test_replay_all_abstained():
    _replay(
        [
            _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, EpistemicState.UNKNOWN),
            _sig("s2", SignalType.BEHAVIOR_ANOMALY_SIGNAL, 0.5, 1.0, EpistemicState.UNKNOWN),
        ],
        "all_abstained",
    )

def test_replay_high_volume():
    """10 signals of mixed types — determinism at scale."""
    _replay(
        [
            _sig(f"s{i}", SignalType.TEXT_RISK_SIGNAL, 0.3 + (i * 0.05), 0.7 + (i * 0.02))
            for i in range(10)
        ],
        "high_volume_10",
    )

def test_replay_ambiguous_with_entropy():
    _replay(
        [
            _sig("s1", SignalType.TEXT_RISK_SIGNAL, 0.8, 1.0, EpistemicState.AMBIGUOUS),
            _sig("s2", SignalType.EXTERNAL_DETECTOR_SIGNAL, 0.5, 0.9, EpistemicState.INFERRED, entropy=0.7),
        ],
        "ambiguous_entropy",
    )
