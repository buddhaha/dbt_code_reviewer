from dbt_reviewer.models import Finding, Severity

ADD_FINDING_TOOL = {
    "name": "add_finding",
    "description": "Add a semantic finding (anti-pattern or concern) discovered during review.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string", "description": "Rule ID, e.g. 'join_fanout'"},
            "severity": {"type": "string", "enum": ["error", "warning", "info"]},
            "line": {"type": "integer", "description": "Line number (optional)"},
            "message": {"type": "string", "description": "Clear, actionable description of the issue"},
        },
        "required": ["rule_id", "severity", "message"],
    }
}

GET_RULES_TOOL = {
    "name": "get_rules",
    "description": "Get dbt review rules from the knowledge base.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "deterministic", "semantic"],
                "description": "Filter rules by category"
            }
        },
        "required": []
    }
}

GET_EXAMPLES_TOOL = {
    "name": "get_examples",
    "description": "Get good and bad code examples for a specific rule.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string", "description": "Rule ID to get examples for"}
        },
        "required": ["rule_id"]
    }
}

AGENT_TOOLS = [ADD_FINDING_TOOL, GET_RULES_TOOL, GET_EXAMPLES_TOOL]


def make_finding_from_tool_input(file_path: str, tool_input: dict) -> Finding:
    return Finding(
        file=file_path,
        line=tool_input.get("line"),
        rule_id=tool_input["rule_id"],
        severity=Severity(tool_input["severity"]),
        message=tool_input["message"],
        source="semantic"
    )
