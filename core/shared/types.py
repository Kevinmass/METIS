from typing import Literal
from dataclasses import dataclass

@dataclass
class TestResult:
    name: str
    statistic: float
    critical_value: float
    alpha: float          # siempre 0.05
    verdict: Literal["ACCEPTED", "REJECTED"]
    detail: dict          # datos adicionales específicos de cada prueba

@dataclass
class GroupVerdict:
    condition: str        # "independence" | "homogeneity" | "trend" | "outliers"
    individual_results: list[TestResult]
    resolved_verdict: Literal["ACCEPTED", "REJECTED", "INCONCLUSIVE"] | None
    hierarchy_applied: bool

@dataclass
class ValidationReport:
    n: int
    warnings: list[dict]
    independence: GroupVerdict
    homogeneity: GroupVerdict
    trend: GroupVerdict
    outliers: GroupVerdict
