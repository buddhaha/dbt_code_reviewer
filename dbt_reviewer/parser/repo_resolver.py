import os
import yaml
from pathlib import Path
from dbt_reviewer.models import ChangedFile


def resolve_files(changed_files: list[ChangedFile], repo_path: str) -> list[ChangedFile]:
    repo = Path(repo_path)
    # Build schema map: model_name -> entry dict
    schema_map = {}
    for schema_file in repo.rglob('schema.yml'):
        try:
            with open(schema_file) as f:
                data = yaml.safe_load(f)
            if data and 'models' in data:
                for model in data['models']:
                    schema_map[model['name']] = model
        except Exception:
            pass

    for cf in changed_files:
        full_path = repo / cf.path
        if full_path.exists():
            cf.full_content = full_path.read_text()
        cf.schema_entry = schema_map.get(cf.model_name)

    return changed_files
