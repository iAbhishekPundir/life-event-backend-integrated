from pathlib import Path
from typing import Any, Dict
import re

import joblib
import pandas as pd


MODEL_DIR = Path(__file__).resolve().parent / "models"


class LifeEventModelPredictor:
    def __init__(self):
        self.models = {}
        self._load_all_models()

    def _load_all_models(self):
        if not MODEL_DIR.exists():
            return

        for model_file in MODEL_DIR.glob("*_confidence_model.pkl"):
            artifact = joblib.load(model_file)
            event_type = artifact.get("event_type")

            if not event_type:
                event_type = self._event_type_from_file_name(model_file.name)

            self.models[event_type] = {
                "model": artifact["model"],
                "feature_columns": artifact["feature_columns"],
                "metrics": artifact.get("metrics", {}),
                "model_path": str(model_file)
            }

    def reload_models(self):
        self.models = {}
        self._load_all_models()

    def is_model_available(self, event_type: str) -> bool:
        return event_type in self.models

    def available_models(self):
        return list(self.models.keys())

    def predict_confidence(
        self,
        event_type: str,
        features: Dict[str, Any]
    ) -> float:
        if not self.is_model_available(event_type):
            raise FileNotFoundError(
                f"No trained model found for event type: {event_type}"
            )

        model_entry = self.models[event_type]
        model = model_entry["model"]
        feature_columns = model_entry["feature_columns"]

        df = pd.DataFrame([features])

        df = pd.get_dummies(
            df,
            columns=[
                "life_event_type",
                "segment",
                "risk_profile"
            ],
            dummy_na=True
        )

        df = df.fillna(0)
        df.columns = [
            self._clean_column_name(column)
            for column in df.columns
        ]

        for column in feature_columns:
            if column not in df.columns:
                df[column] = 0

        df = df[feature_columns]

        if hasattr(model, "predict_proba"):
            confidence_score = model.predict_proba(df)[0][1]
        else:
            confidence_score = model.predict(df)[0]

        return round(float(confidence_score), 2)

    def get_model_metrics(self, event_type: str):
        if not self.is_model_available(event_type):
            return None

        return self.models[event_type].get("metrics", {})

    def _event_type_from_file_name(self, file_name: str) -> str:
        name = file_name.replace("_confidence_model.pkl", "")

        mapping = {
            "marriage": "Marriage",
            "travel": "Travel",
            "birthday": "Birthday",
            "home_purchase": "Home Purchase",
            "education": "Education"
        }

        return mapping.get(name, name)

    def _clean_column_name(self, column_name: str) -> str:
        column_name = str(column_name)
        column_name = re.sub(r"[^A-Za-z0-9_]+", "_", column_name)
        return column_name.strip("_")


model_predictor = LifeEventModelPredictor()