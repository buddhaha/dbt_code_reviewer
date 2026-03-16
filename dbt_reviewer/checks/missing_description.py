from dbt_reviewer.checks.base import BaseCheck
from dbt_reviewer.models import ChangedFile, Finding, Severity


class MissingDescriptionCheck(BaseCheck):
    rule_id = "missing_description"

    def check(self, cf: ChangedFile) -> list[Finding]:
        findings = []
        if cf.schema_entry is None:
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id=self.rule_id,
                severity=Severity.INFO,
                message=f"Model '{cf.model_name}' has no entry in schema.yml — add a description and tests.",
                source="deterministic"
            ))
        elif not cf.schema_entry.get('description'):
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id=self.rule_id,
                severity=Severity.INFO,
                message=f"Model '{cf.model_name}' is missing a description in schema.yml.",
                source="deterministic"
            ))
        return findings
