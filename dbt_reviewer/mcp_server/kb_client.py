import yaml
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"


class KBClient:
    def __init__(self):
        self._rules_cache: Optional[dict] = None

    def _load_all_rules(self) -> dict:
        if self._rules_cache is None:
            self._rules_cache = {}
            for f in (KNOWLEDGE_DIR / "rules").glob("*.yaml"):
                rule = yaml.safe_load(f.read_text())
                if not isinstance(rule, dict):
                    continue

                rule_id = rule.get("id") or f.stem.replace("-", "_")
                self._rules_cache[rule_id] = rule
        return self._rules_cache

    def get_rules(self, category: str = "all") -> dict:
        all_rules = self._load_all_rules()
        if category == "all":
            return all_rules
        return {k: v for k, v in all_rules.items() if v.get("category") == category}

    def get_examples(self, rule_id: str) -> dict:
        rules = self._load_all_rules()
        rule = rules.get(rule_id, {})
        return {
            "rule_id": rule_id,
            "good_examples": rule.get("good_examples", []),
            "bad_examples": rule.get("bad_examples", []),
        }

    def get_prompt(self, name: str, **kwargs) -> str:
        path = KNOWLEDGE_DIR / "prompts" / f"{name}.md"
        template = path.read_text()
        for key, value in kwargs.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template

    def search_patterns(self, query: str) -> list[dict]:
        query_lower = query.lower()
        results = []
        for rule_id, rule in self._load_all_rules().items():
            searchable = f"{rule.get('name','')} {rule.get('description','')}".lower()
            if query_lower in searchable:
                results.append({"rule_id": rule_id, **rule})
        return results

