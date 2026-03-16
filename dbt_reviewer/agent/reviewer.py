import json
from dbt_reviewer.models import ChangedFile, Finding
from dbt_reviewer.agent.tools import AGENT_TOOLS, make_finding_from_tool_input
from dbt_reviewer.mcp_server.kb_client import KBClient
from dbt_reviewer.llm.client import AnthropicClient

SYSTEM_PROMPT = """You are an expert dbt (data build tool) code reviewer.
Your job is to find semantic issues in dbt SQL models that deterministic checks cannot catch.
Focus on:
- Join fanout risk (does this join multiply rows unexpectedly?)
- Data quality concerns (missing WHERE clauses that seem wrong, suspicious NULL handling)
- Model organisation (is this model doing too much? should it be split?)
- Code quality (are there redundant CTEs, unclear aliases?)

Do NOT report issues that were already found by deterministic checks (SELECT *, hardcoded refs, ORDER BY, naming, missing description).
Use the get_rules and get_examples tools to ground your review in dbt best practices.
Use add_finding to record each issue you discover.
When you have finished reviewing, respond with a plain text summary of what you found."""


def run_semantic_review(
    changed_file: ChangedFile,
    deterministic_findings: list[Finding],
    kb_client: KBClient,
    llm_client: AnthropicClient,
) -> list[Finding]:
    semantic_findings = []

    det_summary = "\n".join(
        f"- [{f.severity.value.upper()}] {f.rule_id}: {f.message}"
        for f in deterministic_findings
        if f.file == changed_file.path
    )

    content = changed_file.full_content or '\n'.join(changed_file.added_lines)

    user_message = f"""Review this dbt model: `{changed_file.model_name}`

**File path:** `{changed_file.path}`

**SQL content:**
```sql
{content}
```

**Deterministic checks already found:**
{det_summary or '(none)'}

Please review for semantic issues. Use get_rules to understand best practices, then add_finding for each issue you discover that isn't already covered by the deterministic findings above."""

    messages = [{"role": "user", "content": user_message}]

    # ReAct loop
    for _ in range(10):  # max iterations
        response = llm_client.create_message(
            messages=messages,
            tools=AGENT_TOOLS,
            system=SYSTEM_PROMPT,
        )

        # Collect assistant message content
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            if tool_name == "add_finding":
                finding = make_finding_from_tool_input(changed_file.path, tool_input)
                semantic_findings.append(finding)
                result = {"status": "ok", "finding_added": True}

            elif tool_name == "get_rules":
                category = tool_input.get("category", "all")
                result = kb_client.get_rules(category)

            elif tool_name == "get_examples":
                rule_id = tool_input.get("rule_id", "")
                result = kb_client.get_examples(rule_id)

            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    return semantic_findings
