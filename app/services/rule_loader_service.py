import json
from pathlib import Path
from typing import Any, Dict


class RuleLoaderService:
    """
    Loads configurable rule files from app/rules.

    Rule files:
    - life_event_rules.json
    - recommendation_mappings.json
    - workflow_mappings.json
    - compliance_rules.json
    """

    def __init__(self):
        self.rules_dir = Path(__file__).resolve().parent.parent / "rules"

    def load_json(self, file_name: str) -> Dict[str, Any]:
        file_path = self.rules_dir / file_name

        if not file_path.exists():
            raise FileNotFoundError(
                f"Rule file not found: {file_path}"
            )

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def load_life_event_rules(self) -> Dict[str, Any]:
        return self.load_json("life_event_rules.json")

    def load_recommendation_mappings(self) -> Dict[str, Any]:
        return self.load_json("recommendation_mappings.json")

    def load_workflow_mappings(self) -> Dict[str, Any]:
        return self.load_json("workflow_mappings.json")

    def load_compliance_rules(self) -> Dict[str, Any]:
        return self.load_json("compliance_rules.json")