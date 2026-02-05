# Authority Boundaries – Text Risk Scoring Service

This document establishes **explicit and non-negotiable boundaries** between risk signal generation and decision authority in the Text Risk Scoring Service.

## Core Principle

**The Text Risk Scoring Service is a SIGNAL GENERATOR, not a DECISION MAKER.**

## What This System IS

### ✅ **Risk Signal Provider**
- Generates deterministic risk scores (0.0 - 1.0)
- Provides explainable keyword-based triggers
- Offers structured risk categorization (LOW/MEDIUM/HIGH)
- Delivers consistent, reproducible assessments

### ✅ **Decision Support Tool**
- Provides input for human decision-makers
- Offers structured data for downstream systems
- Enables rule-based filtering pipelines
- Supports content moderation workflows

### ✅ **Demo-Safe Assessment Engine**
- Guarantees predictable behavior for demonstrations
- Provides stable output for evaluation scenarios
- Enables safe integration testing
- Supports proof-of-concept implementations

## What This System IS NOT

### ❌ **Autonomous Decision Authority**
- **NEVER** makes final decisions about content
- **NEVER** determines legal or policy compliance
- **NEVER** replaces human judgment
- **NEVER** provides authoritative risk assessment

### ❌ **Semantic Understanding Engine**
- **CANNOT** understand context or intent
- **CANNOT** detect sarcasm or irony
- **CANNOT** interpret cultural nuances
- **CANNOT** perform linguistic analysis

### ❌ **Legal or Medical Diagnostic Tool**
- **NOT** suitable for legal decision-making
- **NOT** appropriate for medical diagnosis
- **NOT** designed for psychological assessment
- **NOT** intended for regulatory compliance

## Decision Authority Boundaries

### **Human Authority Required For:**
- Content removal or blocking decisions
- Account suspension or termination
- Legal action or reporting
- Policy violation determinations
- Appeals and dispute resolution

### **System Authority Limited To:**
- Keyword pattern detection
- Numerical score generation
- Category classification
- Structured data output
- Deterministic signal provision

## Integration Responsibilities

### **Downstream System Responsibilities:**
- Interpret risk signals appropriately
- Apply business logic and policies
- Make final decisions based on multiple inputs
- Handle appeals and exceptions
- Maintain audit trails for decisions

### **This System's Responsibilities:**
- Provide accurate signal generation
- Maintain deterministic behavior
- Deliver structured, explainable output
- Handle edge cases gracefully
- Preserve system stability

## Liability and Accountability

### **This System Does NOT:**
- Accept liability for downstream decisions
- Guarantee accuracy of risk assessment
- Provide legal or regulatory compliance
- Replace professional judgment
- Assume responsibility for false positives/negatives

### **Users Must:**
- Validate system output against business requirements
- Implement appropriate human oversight
- Maintain decision audit trails
- Handle appeals and corrections
- Accept responsibility for final decisions

## Usage Disclaimers

### **Appropriate Use Cases:**
- Content pre-filtering for human review
- Risk signal aggregation in larger systems
- Demo and evaluation environments
- Development and testing scenarios
- Educational and research purposes

### **Inappropriate Use Cases:**
- Fully automated content moderation
- Legal evidence or compliance checking
- Medical or psychological screening
- Financial fraud detection (as sole input)
- Critical safety or security decisions

## Red Lines - Never Cross These Boundaries

1. **Never use this system as the sole basis for consequential decisions**
2. **Never deploy without human oversight mechanisms**
3. **Never assume semantic understanding of content**
4. **Never rely on this system for legal compliance**
5. **Never use for decisions affecting individual rights without review**

## Integration Checklist

Before deploying this system, ensure:

- [ ] Human review processes are in place
- [ ] Decision audit trails are implemented
- [ ] Appeals mechanisms are available
- [ ] Business logic validation is performed
- [ ] Appropriate disclaimers are provided to end users
- [ ] System limitations are clearly communicated
- [ ] Fallback procedures are defined
- [ ] Regular accuracy validation is scheduled

## Authority Statement

**This system provides risk signals only. All decisions based on these signals remain the full responsibility of the integrating system and its operators.**

**No warranty, guarantee, or assurance is provided regarding the accuracy, completeness, or appropriateness of risk assessments for any specific use case.**

This document serves as the **definitive authority boundary specification** for the Text Risk Scoring Service.