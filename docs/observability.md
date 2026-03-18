# Observability – Text Risk Scoring Service

This document describes how the Text Risk Scoring Service exposes
internal execution visibility in a safe, deterministic, and
privacy-conscious manner.

The goal of observability in this system is to enable reliable
debugging, decision traceability, and post-mortem analysis without
affecting output behavior or introducing nondeterminism.

The observability design of this service aims to:

- Enable reconstruction of risk decisions after execution
- Provide insight into keyword detection and score evolution
- Surface boundary and saturation events explicitly
- Capture unexpected failures without crashing the system
- Preserve determinism and output stability


The system uses structured logging based on Python's built-in
logging module.

Logs are emitted at well-defined decision points rather than
logging raw execution flow. This ensures clarity, signal relevance,
and low operational noise.


The following events are logged during execution:

- Input receipt and normalized input length
- Input truncation due to length limits
- Detection of risk keywords by category
- Category-level score saturation events
- Final risk score and risk category
- Unexpected runtime errors and exceptions


The system uses the following log levels:

- INFO:
  - Keyword detections
  - Final scoring decisions
  - Normal execution milestones

- WARNING:
  - Input truncation events
  - Category score saturation
  - Score clamping events

- ERROR:
  - Invalid input conditions
  - Unexpected runtime exceptions


Each logged event contributes to a traceable decision path.

Given a final output, an engineer can reconstruct:
- Which keywords were detected
- Which categories contributed to the score
- Whether saturation or truncation occurred
- How the final risk category was determined


The observability layer intentionally avoids logging:

- Raw input text
- Personally identifiable information (PII)
- Full keyword lists per request
- User-specific metadata

This ensures privacy preservation and prevents sensitive data
leakage through logs.


Logging is implemented in a side-effect-free manner.

- Log output does not influence scoring logic
- No randomness or timestamps affect decision computation
- Identical inputs always produce identical outputs regardless
  of logging configuration


All known and unknown failure modes are surfaced via logs.

- Anticipated failures are logged with contextual warnings
- Unexpected exceptions are logged with stack traces
- The system always returns a structured error response and
  never crashes


The observability layer enables:

- Debugging incorrect risk categorization
- Investigating false positives or negatives
- Auditing system behavior during demos
- Supporting safe integration with upstream systems


The observability implementation ensures that the Text Risk Scoring
Service remains transparent, explainable, and production-safe.

All decisions are traceable, failures are visible, and system
behavior can be confidently understood without compromising
determinism or privacy.
