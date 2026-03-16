import re
from dbt_reviewer.checks.base import BaseCheck
from dbt_reviewer.models import ChangedFile, Finding, Severity

VALID_PREFIXES = ('stg_', 'int_', 'fct_', 'dim_', 'mart_', 'rpt_', 'base_')


class NamingConventionsCheck(BaseCheck):
    rule_id = "naming_conventions"

    def check(self, cf: ChangedFile) -> list[Finding]:
        findings = []
        name = cf.model_name
        path = cf.path

        # Models in staging/ should start with stg_
        if 'staging' in path and not name.startswith('stg_'):
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                message=f"Model '{name}' in staging/ should be prefixed with 'stg_'.",
                source="deterministic"
            ))

        # Models in intermediate/ should start with int_
        if 'intermediate' in path and not name.startswith('int_'):
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                message=f"Model '{name}' in intermediate/ should be prefixed with 'int_'.",
                source="deterministic"
            ))

        # Models in marts/ should start with fct_, dim_, or mart_
        if 'marts' in path and not any(name.startswith(p) for p in ('fct_', 'dim_', 'mart_', 'rpt_')):
            findings.append(Finding(
                file=cf.path,
                line=None,
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                message=f"Model '{name}' in marts/ should be prefixed with 'fct_', 'dim_', 'mart_', or 'rpt_'.",
                source="deterministic"
            ))

        return findings
