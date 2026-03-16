import re
from dbt_reviewer.checks.base import BaseCheck
from dbt_reviewer.models import ChangedFile, Finding, Severity

NON_FINAL_DIRS = ('staging', 'intermediate', 'base')


class OrderByCheck(BaseCheck):
    rule_id = "order_by_non_final"

    def check(self, cf: ChangedFile) -> list[Finding]:
        findings = []
        path_lower = cf.path.lower()
        is_non_final = any(d in path_lower for d in NON_FINAL_DIRS)
        if not is_non_final:
            return findings

        content = cf.full_content or '\n'.join(cf.added_lines)
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r'\bORDER\s+BY\b', line, re.IGNORECASE):
                # Skip if inside a window function (OVER clause on same line)
                if 'OVER' not in line.upper():
                    findings.append(Finding(
                        file=cf.path,
                        line=i,
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        message="ORDER BY in a non-final model is redundant — dbt doesn't guarantee row order. Remove it or move to the final mart model.",
                        source="deterministic"
                    ))
        return findings
