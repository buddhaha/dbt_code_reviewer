import json
import os
import sys
import click
from dotenv import load_dotenv

load_dotenv()
from dbt_reviewer.parser.diff_parser import parse_diff
from dbt_reviewer.parser.repo_resolver import resolve_files
from dbt_reviewer.checks.runner import run_deterministic_checks
from dbt_reviewer.output.formatter import to_json


@click.command()
@click.option('--repo-path', default='.', help='Path to the dbt project root')
@click.option('--no-llm', is_flag=True, default=False, help='Skip semantic agent (deterministic checks only)')
@click.option('--diff', 'diff_file', type=click.File('r'), default='-', help='Diff file (default: stdin)')
def main(repo_path, no_llm, diff_file):
    """DBT Code Reviewer — hybrid deterministic + LLM review of dbt model changes."""
    diff_text = diff_file.read()

    changed_files = parse_diff(diff_text)
    if not changed_files:
        click.echo(json.dumps({"findings": [], "summary": {"total": 0, "errors": 0, "warnings": 0, "infos": 0}}, indent=2))
        return

    changed_files = resolve_files(changed_files, repo_path)

    findings = run_deterministic_checks(changed_files)

    if not no_llm:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            click.echo(
                "Error: ANTHROPIC_API_KEY is not set. "
                "Export it before running or use --no-llm to skip semantic review.\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...",
                err=True,
            )
            sys.exit(1)

        try:
            from dbt_reviewer.mcp_server.kb_client import KBClient
            from dbt_reviewer.llm.client import AnthropicClient
            from dbt_reviewer.agent.reviewer import run_semantic_review

            kb_client = KBClient()
            llm_client = AnthropicClient()

            for cf in changed_files:
                semantic_findings = run_semantic_review(cf, findings, kb_client, llm_client)
                findings.extend(semantic_findings)
        except Exception as e:
            click.echo(f"Error: semantic review failed: {e}", err=True)
            sys.exit(1)

    click.echo(to_json(findings))
