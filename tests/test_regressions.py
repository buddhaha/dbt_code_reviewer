import unittest
import importlib
import sys
from types import ModuleType
from types import SimpleNamespace

from dbt_reviewer.checks.hardcoded_refs import HardcodedRefsCheck
from dbt_reviewer.mcp_server.kb_client import KBClient
from dbt_reviewer.models import ChangedFile, DiffHunk, Finding, Severity
from dbt_reviewer.output.formatter import deduplicate


def make_changed_file(content: str) -> ChangedFile:
    return ChangedFile(
        path="models/staging/stg_example.sql",
        model_name="stg_example",
        is_sql=True,
        is_new_file=False,
        added_lines=content.splitlines(),
        hunks=[DiffHunk(start_line=1, content=content)],
        full_content=content,
    )


class RegressionTests(unittest.TestCase):
    def test_kb_client_uses_yaml_rule_id(self):
        client = KBClient()

        examples = client.get_examples("join_fanout")

        self.assertTrue(examples["good_examples"])
        self.assertTrue(examples["bad_examples"])

    def test_server_supports_underscored_rule_ids(self):
        fastmcp_module = ModuleType("fastmcp")

        class FastMCPStub:
            def __init__(self, *_args, **_kwargs):
                pass

            def tool(self):
                return lambda func: func

            def resource(self, *_args, **_kwargs):
                return lambda func: func

            def prompt(self):
                return lambda func: func

        fastmcp_module.FastMCP = FastMCPStub
        original = sys.modules.get("fastmcp")
        sys.modules["fastmcp"] = fastmcp_module

        try:
            server = importlib.import_module("dbt_reviewer.mcp_server.server")
        finally:
            if original is None:
                sys.modules.pop("fastmcp", None)
            else:
                sys.modules["fastmcp"] = original

        examples = server.get_examples("join_fanout")

        self.assertTrue(examples["good_examples"])
        self.assertTrue(examples["bad_examples"])

    def test_server_review_model_replaces_all_placeholders(self):
        fastmcp_module = ModuleType("fastmcp")

        class FastMCPStub:
            def __init__(self, *_args, **_kwargs):
                pass

            def tool(self):
                return lambda func: func

            def resource(self, *_args, **_kwargs):
                return lambda func: func

            def prompt(self):
                return lambda func: func

        fastmcp_module.FastMCP = FastMCPStub
        original = sys.modules.get("fastmcp")
        sys.modules["fastmcp"] = fastmcp_module

        try:
            server = importlib.import_module("dbt_reviewer.mcp_server.server")
        finally:
            if original is None:
                sys.modules.pop("fastmcp", None)
            else:
                sys.modules["fastmcp"] = original

        prompt = server.review_model(
            "stg_orders",
            "select 1",
            "models/staging/stg_orders.sql",
            "- [WARNING] select_star: Avoid SELECT *",
        )

        self.assertIn("models/staging/stg_orders.sql", prompt)
        self.assertIn("- [WARNING] select_star: Avoid SELECT *", prompt)
        self.assertNotIn("{{file_path}}", prompt)
        self.assertNotIn("{{det_summary}}", prompt)

    def test_no_ref_or_source_triggers_without_hardcoded_ref(self):
        finding = make_changed_file(
            "with ids as (select 1 as id)\nselect id\nfrom ids\n"
        )

        findings = HardcodedRefsCheck().check(finding)

        self.assertIn("no_ref_or_source", {item.rule_id for item in findings})

    def test_deduplicate_keeps_distinct_messages_on_same_line(self):
        findings = [
            Finding(
                file="models/example.sql",
                line=10,
                rule_id="hardcoded_refs",
                severity=Severity.ERROR,
                message="Hardcoded reference 'raw.a'.",
                source="deterministic",
            ),
            Finding(
                file="models/example.sql",
                line=10,
                rule_id="hardcoded_refs",
                severity=Severity.ERROR,
                message="Hardcoded reference 'raw.b'.",
                source="deterministic",
            ),
        ]

        deduped = deduplicate(findings)

        self.assertEqual(2, len(deduped))

    def test_review_prompt_replaces_model_name(self):
        client = KBClient()
        prompt = client.get_prompt(
            "review-model",
            model_name="stg_orders",
            file_path="models/staging/stg_orders.sql",
            model_sql="select 1",
            det_summary="(none)",
        )

        self.assertIn("stg_orders", prompt)
        self.assertNotIn("{{model_name}}", prompt)

    def test_semantic_review_reports_local_tool_activity(self):
        anthropic_module = ModuleType("anthropic")
        anthropic_module.Anthropic = object
        anthropic_module.types = SimpleNamespace(Message=object)
        original_anthropic = sys.modules.get("anthropic")
        sys.modules["anthropic"] = anthropic_module

        try:
            reviewer = importlib.import_module("dbt_reviewer.agent.reviewer")
        finally:
            if original_anthropic is None:
                sys.modules.pop("anthropic", None)
            else:
                sys.modules["anthropic"] = original_anthropic

        class FakeLLMClient:
            def __init__(self):
                self.calls = 0

            def create_message(self, **_kwargs):
                self.calls += 1
                if self.calls > 1:
                    return SimpleNamespace(
                        stop_reason="end_turn",
                        content=[],
                    )

                return SimpleNamespace(
                    stop_reason="tool_use",
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            id="tool-1",
                            name="get_rules",
                            input={"category": "semantic"},
                        ),
                        SimpleNamespace(
                            type="tool_use",
                            id="tool-2",
                            name="add_finding",
                            input={
                                "rule_id": "join_fanout",
                                "severity": "warning",
                                "message": "Potential fanout.",
                            },
                        ),
                    ],
                )

        class FakeKBClient:
            def get_rules(self, _category):
                return {"join_fanout": {"id": "join_fanout"}}

            def get_examples(self, _rule_id):
                return {}

            def get_prompt(self, _name, **_kwargs):
                return "Rendered prompt"

        status_messages = []
        findings = reviewer.run_semantic_review(
            make_changed_file("select 1"),
            [],
            FakeKBClient(),
            FakeLLMClient(),
            status_callback=status_messages.append,
        )

        self.assertEqual(1, len(findings))
        self.assertTrue(
            any("loading knowledge locally" in message for message in status_messages)
        )
        self.assertTrue(
            any("recording semantic finding locally" in message for message in status_messages)
        )


if __name__ == "__main__":
    unittest.main()
