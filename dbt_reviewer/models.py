from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DiffHunk:
    start_line: int
    content: str


@dataclass
class ChangedFile:
    path: str           # relative path like "models/staging/stg_bad_orders.sql"
    model_name: str     # "stg_bad_orders"
    is_sql: bool
    is_new_file: bool
    added_lines: list[str]
    hunks: list[DiffHunk]
    full_content: Optional[str] = None   # loaded from repo_path
    schema_entry: Optional[dict] = None  # loaded from schema.yml


@dataclass
class Finding:
    file: str
    line: Optional[int]
    rule_id: str
    severity: Severity
    message: str
    source: str  # "deterministic" or "semantic"
