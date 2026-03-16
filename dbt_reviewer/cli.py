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


def emit_status(message: str) -> None:
    click.echo(f"[dbt-reviewer] {message}", err=True)


@click.command()
@click.option('--repo-path', default='.', help='Path to the dbt project root')
@click.option('--no-llm', is_flag=True, default=False, help='Skip semantic agent (deterministic checks only)')
@click.option('--diff', 'diff_file', type=click.File('r'), default='-', help='Diff file (default: stdin)')
def main(repo_path, no_llm, diff_file):
    """DBT Code Reviewer — hybrid deterministic + LLM review of dbt model changes."""
    emit_status("Reading diff input")
    diff_text = diff_file.read()

    emit_status("Parsing changed SQL files from diff")
    changed_files = parse_diff(diff_text)
    if not changed_files:
        emit_status("No changed SQL files found")
        click.echo(json.dumps({"findings": [], "summary": {"total": 0, "errors": 0, "warnings": 0, "infos": 0}}, indent=2))
        return

    emit_status(f"Loaded {len(changed_files)} changed SQL file(s)")
    emit_status(f"Resolving full file contents and schema metadata from '{repo_path}'")
    changed_files = resolve_files(changed_files, repo_path)

    emit_status("Running deterministic checks")
    findings = run_deterministic_checks(changed_files)
    emit_status(f"Deterministic checks produced {len(findings)} finding(s)")

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

            emit_status("Starting semantic review agent")
            for index, cf in enumerate(changed_files, 1):
                emit_status(
                    f"Semantic review {index}/{len(changed_files)}: {cf.path}"
                )
                semantic_findings = run_semantic_review(
                    cf,
                    findings,
                    kb_client,
                    llm_client,
                    status_callback=emit_status,
                )
                findings.extend(semantic_findings)
                emit_status(
                    f"Semantic review finished for {cf.path} with {len(semantic_findings)} finding(s)"
                )
        except Exception as e:
            click.echo(f"Error: semantic review failed: {e}", err=True)
            emit_status(f"Outputting {len(findings)} deterministic finding(s) without semantic results")
            click.echo(to_json(findings))
            sys.exit(1)
    else:
        emit_status("Skipping semantic review (--no-llm)")

    emit_status(f"Formatting final output with {len(findings)} total finding(s)")
    click.echo(to_json(findings))
