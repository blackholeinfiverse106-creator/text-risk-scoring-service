from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PolicyState:
    policy_version: int
    category_weights: Dict[str, float]
    confidence_multiplier: float
    update_count: int
