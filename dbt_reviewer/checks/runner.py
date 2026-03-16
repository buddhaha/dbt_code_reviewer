from dbt_reviewer.models import ChangedFile, Finding
from dbt_reviewer.checks.select_star import SelectStarCheck
from dbt_reviewer.checks.hardcoded_refs import HardcodedRefsCheck
from dbt_reviewer.checks.naming_conventions import NamingConventionsCheck
from dbt_reviewer.checks.missing_description import MissingDescriptionCheck
from dbt_reviewer.checks.order_by import OrderByCheck

ALL_CHECKS = [
    SelectStarCheck(),
    HardcodedRefsCheck(),
    NamingConventionsCheck(),
    MissingDescriptionCheck(),
    OrderByCheck(),
]


def run_deterministic_checks(changed_files: list[ChangedFile]) -> list[Finding]:
    findings = []
    for cf in changed_files:
        for check in ALL_CHECKS:
            findings.extend(check.check(cf))
    return findings
