import re
from dbt_reviewer.checks.base import BaseCheck
from dbt_reviewer.models import ChangedFile, Finding, Severity


class HardcodedRefsCheck(BaseCheck):
    rule_id = "hardcoded_refs"

    # Pattern: FROM or JOIN followed by a dotted path (schema.table or db.schema.table)
    # but NOT preceded by ref( or source(
    HARDCODED_PATTERN = re.compile(
        r'\b(FROM|JOIN)\s+(?![\w]+\s*\()'  # FROM/JOIN not followed by function call
        r'([\w]+\.[\w.]+)',                   # dotted path
        re.IGNORECASE
    )
    REF_SOURCE_PATTERN = re.compile(r'\{\{\s*(ref|source)\s*\(', re.IGNORECASE)

    def check(self, cf: ChangedFile) -> list[Finding]:
        findings = []
        content = cf.full_content or '\n'.join(cf.added_lines)
        has_ref_or_source = bool(self.REF_SOURCE_PATTERN.search(content))
        has_from_or_join = False

        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r'\b(FROM|JOIN)\b', line, re.IGNORECASE):
                has_from_or_join = True

            m = self.HARDCODED_PATTERN.search(line)
            if m:
                findings.append(Finding(
                    file=cf.path,
                    line=i,
                    rule_id=self.rule_id,
                    severity=Severity.ERROR,
                    message=f"Hardcoded reference '{m.group(2)}' — use {{{{ ref('model') }}}} or {{{{ source('src', 'table') }}}} instead.",
                    source="deterministic"
                ))

        if not has_ref_or_source and has_from_or_join:
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id="no_ref_or_source",
                severity=Severity.ERROR,
                message="Model contains no ref() or source() calls — all upstream dependencies must use dbt's dependency resolution.",
                source="deterministic"
            ))

        return findings
