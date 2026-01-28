# Failure Bounds – Text Risk Scoring Service

This document defines the explicit boundaries beyond which
the system's outputs should not be considered reliable.

## Input Assumptions

The system assumes:
- Input text is human-readable natural language
- Input is predominantly in English
- Input is not intentionally obfuscated beyond keyword recognition

Violation of these assumptions may reduce reliability.

## Semantic Limits

The system does not perform semantic understanding.
It cannot reliably interpret:
- Sarcasm or humor
- Metaphors or idioms
- Contextual intent
- Quoted or hypothetical statements

## Adversarial Limits

The system may produce unreliable results when:
- Keywords are intentionally masked or obfuscated
- Conflicting signals are deliberately injected
- Euphemisms replace explicit risk terms

## Confidence Limits

Risk scores reflect keyword-based signal presence.
They do not represent certainty, probability, or intent.

Low confidence scenarios may still produce moderate risk scores.

## Conclusion

These bounds define where human review or higher-level systems
should take precedence over automated scoring.
