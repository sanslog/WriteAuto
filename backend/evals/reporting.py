"""Small reporting model shared by agent evaluation cases."""

from __future__ import annotations

from dataclasses import dataclass, field

import logging

logger = logging.getLogger(__name__)


@dataclass
class EvalReport:
    """A named collection of evaluated assertions."""

    name: str
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append((name, bool(passed), detail))

    @property
    def passed(self) -> bool:
        passed = all(item[1] for item in self.checks)
        if not passed:
            logger.warning("Agent evaluation failed:\n%s", self.summary())
        return passed

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for item in self.checks if item[1]) / len(self.checks)

    def summary(self) -> str:
        lines = [f"{self.name}: score={self.score:.0%}, passed={self.passed}"]
        lines.extend(
            f"  [{'PASS' if passed else 'FAIL'}] {name}{f' - {detail}' if detail else ''}"
            for name, passed, detail in self.checks
        )
        return "\n".join(lines)


def assert_report(report: EvalReport) -> None:
    if not report.passed:
        raise AssertionError(report.summary())
