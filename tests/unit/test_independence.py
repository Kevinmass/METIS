from core.shared.types import TestResult as ValidationTestResult
from core.validation.independence import resolve_independence


def make_result(name: str, verdict: str) -> ValidationTestResult:
    return ValidationTestResult(
        name=name,
        statistic=0.0,
        critical_value=1.0,
        alpha=0.05,
        verdict=verdict,
        detail={},
    )


def test_resolve_independence_accepts_when_anderson_accepts_and_ww_rejects():
    anderson = make_result("Anderson Autocorrelation Test", "ACCEPTED")
    ww = make_result("Wald-Wolfowitz Runs Test", "REJECTED")

    report = resolve_independence(anderson, ww)

    assert report.resolved_verdict == "ACCEPTED"
    assert report.hierarchy_applied is True
