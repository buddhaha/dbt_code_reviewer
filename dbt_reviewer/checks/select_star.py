import re
from dbt_reviewer.checks.base import BaseCheck
from dbt_reviewer.models import ChangedFile, Finding, Severity


class SelectStarCheck(BaseCheck):
    rule_id = "select_star"

    def check(self, cf: ChangedFile) -> list[Finding]:
        findings = []
        content = cf.full_content or '\n'.join(cf.added_lines)
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r'\bSELECT\s+\*', line, re.IGNORECASE):
                findings.append(Finding(
                    file=cf.path,
                    line=i,
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    message="Avoid SELECT * — list columns explicitly for deterministic output and performance.",
                    source="deterministic"
                ))
        return findings
