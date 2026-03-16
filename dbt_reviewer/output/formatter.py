import json
from dbt_reviewer.models import Finding, Severity

SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}


def deduplicate(findings: list[Finding]) -> list[Finding]:
    seen = set()
    result = []
    for f in findings:
        key = (f.file, f.line, f.rule_id, f.severity, f.message)
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.file, f.line or 0))


def to_json(findings: list[Finding]) -> str:
    deduped = deduplicate(findings)
    sorted_findings = sort_findings(deduped)
    output = {
        "findings": [
            {
                "file": f.file,
                "line": f.line,
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "message": f.message,
                "source": f.source,
            }
            for f in sorted_findings
        ],
        "summary": {
            "total": len(sorted_findings),
            "errors": sum(1 for f in sorted_findings if f.severity == Severity.ERROR),
            "warnings": sum(1 for f in sorted_findings if f.severity == Severity.WARNING),
            "infos": sum(1 for f in sorted_findings if f.severity == Severity.INFO),
        }
    }
    return json.dumps(output, indent=2)
