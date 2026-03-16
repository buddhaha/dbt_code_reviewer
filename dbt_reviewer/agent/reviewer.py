import json
from typing import Callable, Optional
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
    status_callback: Optional[Callable[[str], None]] = None,
) -> list[Finding]:
    semantic_findings = []

    def emit_status(message: str) -> None:
        if status_callback is not None:
            status_callback(message)

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

    MAX_ITERATIONS = 10
    # ReAct loop
    for iteration in range(MAX_ITERATIONS):
        emit_status(
            f"Agent turn {iteration + 1}: sending prompt to Anthropic with tool definitions"
        )
        response = llm_client.create_message(
            messages=messages,
            tools=AGENT_TOOLS,
            system=SYSTEM_PROMPT,
        )

        # Collect assistant message content
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            emit_status("Agent finished without requesting more tools")
            break

        if response.stop_reason != "tool_use":
            emit_status(f"Agent stopped with reason '{response.stop_reason}'")
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            if tool_name == "add_finding":
                emit_status("Agent requested add_finding; recording semantic finding locally")
                finding = make_finding_from_tool_input(changed_file.path, tool_input)
                semantic_findings.append(finding)
                result = {"status": "ok", "finding_added": True}

            elif tool_name == "get_rules":
                category = tool_input.get("category", "all")
                emit_status(
                    f"Agent requested get_rules(category='{category}'); loading knowledge locally"
                )
                result = kb_client.get_rules(category)

            elif tool_name == "get_examples":
                rule_id = tool_input.get("rule_id", "")
                emit_status(
                    f"Agent requested get_examples(rule_id='{rule_id}'); loading knowledge locally"
                )
                result = kb_client.get_examples(rule_id)

            else:
                emit_status(f"Agent requested unsupported tool '{tool_name}'")
                result = {"error": f"Unknown tool: {tool_name}"}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        emit_status("Returning tool results to Anthropic for the next agent step")
        messages.append({"role": "user", "content": tool_results})
    else:
        emit_status(f"Warning: agent reached max iterations ({MAX_ITERATIONS}) without finishing")

    return semantic_findings
