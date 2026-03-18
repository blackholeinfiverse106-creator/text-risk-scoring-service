# Confidence Model – Text Risk Scoring Service

## Purpose

This document defines how the system estimates confidence in its
risk assessment independently of the risk score itself.

Risk represents potential harm.
Confidence represents how certain the system is about that assessment.

These two concepts are intentionally separated.

---

## Definition of Confidence

Confidence is a deterministic measure of the quality and clarity
of evidence supporting the computed risk score.

Confidence is NOT:
- A probability
- A prediction of intent
- A measure of correctness

Confidence reflects uncertainty in interpretation, not uncertainty
in execution.

---

## Factors That Increase Confidence

Confidence increases when:
- Multiple risk keywords are detected
- Risk indicators are consistent in direction
- Keywords appear clearly and unambiguously
- Signals reinforce a single interpretation

Example:
A message containing multiple explicit fraud keywords
produces higher confidence than a message containing a single keyword.

---

## Factors That Decrease Confidence

Confidence decreases when:
- Only a single keyword is detected
- Keywords appear across unrelated categories
- Signals are weak or isolated
- Language may be idiomatic or ambiguous
- Risk indicators conflict with benign context

Example:
The phrase "kill time with friends" contains a risk keyword
but is likely benign, resulting in lower confidence.

---

## Determinism Guarantee

The confidence score is fully deterministic.

For identical input text and configuration:
- risk_score is identical
- confidence_score is identical

No randomness or external state influences confidence estimation.

---

## Interpretation Guidelines

- High risk with low confidence indicates ambiguous but potentially harmful content
- Low risk with high confidence indicates clearly benign content
- Confidence should always be interpreted alongside risk_score

Confidence does not modify risk_score.
It provides additional context for downstream decision-making.

---

## Design Rationale

The confidence model is intentionally conservative.

When uncertainty exists, confidence is reduced rather than risk
being artificially increased.

This design prevents over-escalation and supports safe integration
in decision pipelines.
\.\.\.\.