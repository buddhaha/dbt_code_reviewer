from abc import ABC, abstractmethod
from dbt_reviewer.models import ChangedFile, Finding


class BaseCheck(ABC):
    rule_id: str

    @abstractmethod
    def check(self, changed_file: ChangedFile) -> list[Finding]:
        pass
