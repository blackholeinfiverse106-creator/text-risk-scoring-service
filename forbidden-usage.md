# Forbidden Usage Matrix

## 1. Prohibited Actions (The "Never" List)
Any attempt to use the service in the following ways constitutes a breach of the safety contract:

| Pattern | Description | Rationale |
| :--- | :--- | :--- |
| **Auto-Ban** | Automatically banning users based solely on `risk_score` > Threshold. | No human-in-the-loop; high false positive risk. |
| **Legal Admissibility** | Using scores as evidence in legal proceedings. | System is a heuristic signal, not a forensic tool. |
| **Sole Truth** | Treating `risk_category` as the absolute classification of content. | Ignores context and intent (e.g. news reporting). |
| **Feedback Loops** | Training the engine on its own output. | Model collapse and bias amplification. |

## 2. Misuse Scenarios (Contextual)
| Scenario | Status | Why? |
| :--- | :--- | :--- |
| "I want to filter spam on my blog." | **ALLOWED** | Low stakes, spam is well-defined. |
| "I want to report users to police for 'Terrorism' score." | **FORBIDDEN** | High stakes, requires human validation. |
| "I want to hide comments until reviewed." | **ALLOWED** | "Queueing" is safe; "Deleting" is not. |

## 3. Technical Enforcements
The system actively rejects:
- Context fields implying executive power (`role="admin"`, `action="ban"`).
- Requests trying to override risk scores (`override_risk=0.0`).
- Roles that imply authority (`judge`, `enforcer`).
