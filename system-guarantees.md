# System Guarantees – Text Risk Scoring Service

This document explicitly defines what the system guarantees
and what it intentionally does not guarantee.

The goal is to ensure safe integration and prevent misuse.


## Guaranteed Behaviors

The system guarantees the following:

- Deterministic output for identical input
- Structured response under all conditions
- No unhandled exceptions or crashes
- Bounded risk_score between 0.0 and 1.0
- Explainable decisions via trigger_reasons
- Graceful handling of invalid and empty input


## Non-Guaranteed Behaviors

The system does NOT guarantee:

- Semantic understanding of text
- Contextual or intent awareness
- Absence of false positives
- Absence of false negatives
- Linguistic completeness or multilingual support


## Determinism Boundary

The system is fully deterministic with respect to:
- Input text
- Keyword configuration
- Scoring thresholds

No randomness or external state influences the output.


## Stress & Boundary Conditions

- Input text exceeding safe limits is truncated deterministically
- Keyword saturation is capped per category
- Score accumulation is bounded and normalized


## Intended Usage

This system is designed for:
- Demo-safe risk scoring
- Rule-based AI decision pipelines
- Application-layer filtering and moderation

It is not intended for autonomous decision-making
or legal, medical, or psychological diagnosis.

## Guarantees Under Adversarial Conditions

The system guarantees:
- Deterministic behavior even under adversarial input
- Stable output under repeated execution
- Bounded scoring regardless of keyword saturation

The system does NOT guarantee:
- Accurate intent detection under adversarial phrasing
- Robustness against semantic obfuscation
- Correct interpretation of ambiguous language
