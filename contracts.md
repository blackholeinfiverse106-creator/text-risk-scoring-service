# Text Risk Scoring Service – Contracts

## Input Schema
{
  "text": "string (required, max 5000 chars)"
}

## Output Schema
{
  "risk_score": "float (0–1)",
  "risk_category": "LOW | MEDIUM | HIGH",
  "trigger_reasons": ["string"],
  "processed_length": "int",
  "errors": null | object
}

## Error Schema
{
  "error_code": "EMPTY_INPUT | INVALID_TYPE | TOO_LONG",
  "message": "string"
}

## Guarantees
- Service never crashes
- Always returns structured response
- Same input produces same output
