# Adversarial Input Taxonomy – Text Risk Scoring Service

This document enumerates classes of adversarial and ambiguous inputs
that may attempt to confuse, exploit, or mislead the Text Risk Scoring Service.

The goal is not to eliminate uncertainty, but to explicitly reason
about it and design safe system behavior under ambiguity.

<!-- ## A-01: Ambiguous Language -->

**Description:**  
Inputs that contain words or phrases with both benign and harmful meanings
depending on context.

**Examples:**  
- "I want to kill time"
- "This game is bomb"
- "That idea is deadly good"

**Risk to System:**  
Keyword-based detection may incorrectly classify benign content as high risk.

**Current Handling Strategy:**  
- Keyword detection triggers risk signals
- No semantic disambiguation is performed

**Residual Uncertainty:**  
The system cannot determine user intent from ambiguous language alone.

**Design Rationale:**  
The system prefers conservative detection over semantic interpretation
to preserve determinism and avoid false guarantees.


<!-- ## A-02: Mixed-Signal Inputs -->

**Description:**  
Inputs containing both mitigating and risky signals simultaneously.

**Examples:**  
- "I hate violence but I want to kill him"
- "Fraud is bad but scams work"

**Risk to System:**  
Conflicting signals may lead to unclear categorization.

**Current Handling Strategy:**  
- Risk signals are accumulated deterministically
- Mitigating language does not reduce score

**Residual Uncertainty:**  
The system cannot weigh moral stance or intent.

**Design Rationale:**  
Risk presence is treated independently of sentiment to avoid manipulation.


<!-- ## A-03: Intent Masking and Sarcasm -->

**Description:**  
Inputs where risky language is masked using humor, sarcasm, or disclaimers.

**Examples:**  
- "Just joking, but I will kill you"
- "This is purely academic — how to make a bomb"

**Risk to System:**  
Sarcasm and disclaimers may falsely appear as benign context.

**Current Handling Strategy:**  
- Literal text analysis only
- No sarcasm detection

**Residual Uncertainty:**  
Sarcasm cannot be reliably detected without probabilistic models.

**Design Rationale:**  
The system avoids intent inference to maintain predictable behavior.

<!-- ## A-04: Semantic Evasion -->

**Description:**  
Inputs that convey harmful intent without using known keywords.

**Examples:**  
- "Make him disappear"
- "Teach them a permanent lesson"

**Risk to System:**  
Keyword-based detection may miss implied threats.

**Current Handling Strategy:**  
- No detection (by design)

**Residual Uncertainty:**  
System may under-detect risk in euphemistic language.

**Design Rationale:**  
Avoiding speculative interpretation is preferred over false certainty.

<!-- ## A-05: Repetition and Stress Inputs -->

**Description:**  
Repeated submission of the same or similar inputs to test stability.

**Examples:**  
- Identical inputs sent many times
- Slight variations to detect drift

**Risk to System:**  
Potential nondeterminism or state leakage.

**Current Handling Strategy:**  
- Stateless processing
- Deterministic logic

**Residual Uncertainty:**  
None — determinism guarantees stable output.

**Design Rationale:**  
Stateless design ensures repeatability under stress.

## Summary

The system explicitly acknowledges adversarial and ambiguous inputs.
It does not attempt to infer intent, sarcasm, or semantics beyond
literal text matching.

This design prioritizes:
- Determinism
- Explainability
- Bounded behavior
- Honest uncertainty

Ambiguity is surfaced, not hidden.
