from fastmcp import FastMCP
import yaml
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"

mcp = FastMCP("dbt-reviewer-kb")


def _load_rule(rule_id: str) -> dict:
    for candidate in {rule_id, rule_id.replace("_", "-")}:
        path = KNOWLEDGE_DIR / "rules" / f"{candidate}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text())
    return {}


def _load_all_rules() -> dict[str, dict]:
    rules = {}
    for f in (KNOWLEDGE_DIR / "rules").glob("*.yaml"):
        rule = yaml.safe_load(f.read_text())
        if not isinstance(rule, dict):
            continue

        rule_id = rule.get("id") or f.stem.replace("-", "_")
        rules[rule_id] = rule
    return rules


@mcp.tool()
def get_rules(category: str = "all") -> dict:
    """Get dbt review rules. category: 'all', 'deterministic', or 'semantic'"""
    all_rules = _load_all_rules()
    if category == "all":
        return all_rules
    return {k: v for k, v in all_rules.items() if v.get("category") == category}


@mcp.tool()
def get_examples(rule_id: str) -> dict:
    """Get good/bad examples for a specific rule."""
    rule = _load_rule(rule_id)
    return {
        "rule_id": rule_id,
        "good_examples": rule.get("good_examples", []),
        "bad_examples": rule.get("bad_examples", []),
    }


@mcp.tool()
def search_patterns(query: str) -> list[dict]:
    """Search rules by keyword in name or description."""
    query_lower = query.lower()
    results = []
    for rule_id, rule in _load_all_rules().items():
        searchable = f"{rule.get('name','')} {rule.get('description','')}".lower()
        if query_lower in searchable:
            results.append({"rule_id": rule_id, **rule})
    return results


@mcp.resource("rules://select-star")
def resource_select_star() -> str:
    return yaml.dump(_load_rule("select-star"))


@mcp.resource("rules://hardcoded-refs")
def resource_hardcoded_refs() -> str:
    return yaml.dump(_load_rule("hardcoded-refs"))


@mcp.resource("rules://join-fanout")
def resource_join_fanout() -> str:
    return yaml.dump(_load_rule("join-fanout"))


@mcp.resource("rules://naming-conventions")
def resource_naming_conventions() -> str:
    return yaml.dump(_load_rule("naming-conventions"))


@mcp.resource("rules://missing-description")
def resource_missing_description() -> str:
    return yaml.dump(_load_rule("missing-description"))


@mcp.resource("rules://order-by-non-final")
def resource_order_by() -> str:
    return yaml.dump(_load_rule("order-by-non-final"))


@mcp.prompt()
def review_model(model_name: str, model_sql: str) -> str:
    # use promp template instead of hardcoded string
    template_path = KNOWLEDGE_DIR / "prompts" / "review-model.md"
    template = template_path.read_text()
    return template.replace("{{model_name}}", model_name).replace("{{model_sql}}", model_sql)



if __name__ == "__main__":
    mcp.run()
