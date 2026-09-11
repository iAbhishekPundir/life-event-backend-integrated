from pathlib import Path
import re

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except Exception:
    from sklearn.ensemble import GradientBoostingClassifier
    LIGHTGBM_AVAILABLE = False

from app.ml.training_dataset import training_dataset_builder


MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

EVENT_TYPES = [
    "Marriage",
    "Travel",
    "Birthday",
    "Home Purchase",
    "Education"
]


class PerEventModelTrainer:
    def train_all(self):
        df = training_dataset_builder.load_training_dataframe()

        results = {}

        for event_type in EVENT_TYPES:
            print("")
            print(f"Training model for: {event_type}")

            event_df = df[df["life_event_type"] == event_type].copy()

            if event_df.empty:
                print(f"No rows found for {event_type}. Skipping.")
                continue

            balanced_df = self._balance_dataset(event_df)

            if balanced_df["label"].nunique() < 2:
                print(f"Not enough label diversity for {event_type}. Skipping.")
                continue

            artifact = self._train_event_model(event_type, balanced_df)
            results[event_type] = artifact["metrics"]

        print("")
        print("Per-event training completed.")
        print(results)

        return results

    def _balance_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        positive_df = df[df["label"] == 1]
        negative_df = df[df["label"] == 0]

        sample_size = min(len(positive_df), len(negative_df), 60)

        if sample_size == 0:
            return df

        positive_sample = positive_df.sample(
            n=sample_size,
            random_state=42
        )

        negative_sample = negative_df.sample(
            n=sample_size,
            random_state=42
        )

        balanced_df = pd.concat(
            [positive_sample, negative_sample],
            ignore_index=True
        )

        return balanced_df.sample(
            frac=1,
            random_state=42
        ).reset_index(drop=True)

    def _train_event_model(self, event_type: str, df: pd.DataFrame):
        X, y = self._prepare_features(df)

        X_train, X_val, X_test, y_train, y_val, y_test = self._split_dataset(X, y)

        model, model_type = self._build_model()

        model.fit(X_train, y_train)

        validation_metrics = self._evaluate(model, X_val, y_val)
        test_metrics = self._evaluate(model, X_test, y_test)

        feature_importance = self._get_feature_importance(model, X)

        safe_event_name = self._safe_name(event_type)
        model_path = MODEL_DIR / f"{safe_event_name}_confidence_model.pkl"

        artifact = {
            "model": model,
            "model_type": model_type,
            "event_type": event_type,
            "feature_columns": list(X.columns),
            "validation_metrics": validation_metrics,
            "metrics": test_metrics,
            "feature_importance": feature_importance,
            "training_rows": len(df),
            "label_distribution": y.value_counts().to_dict()
        }

        joblib.dump(artifact, model_path)

        print(f"Saved model: {model_path}")
        print(f"Rows: {len(df)}")
        print(f"Label distribution: {y.value_counts().to_dict()}")
        print(f"Validation metrics: {validation_metrics}")
        print(f"Test metrics: {test_metrics}")

        print("Top features:")
        for feature, importance in list(feature_importance.items())[:10]:
            print(f"{feature}: {importance}")

        return artifact

    def _split_dataset(self, X, y):
        """
        Split dataset into:
        - 70% train
        - 15% validation
        - 15% test
        """

        X_train, X_temp, y_train, y_temp = train_test_split(
            X,
            y,
            test_size=0.30,
            random_state=42,
            stratify=y
        )

        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=0.50,
            random_state=42,
            stratify=y_temp
        )

        return X_train, X_val, X_test, y_train, y_val, y_test

    def _build_model(self):
        if LIGHTGBM_AVAILABLE:
            model = LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=4,
                min_child_samples=1,
                min_data_in_bin=1,
                class_weight="balanced",
                random_state=42,
                force_col_wise=True
            )
            return model, "LightGBM"

        model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )

        return model, "GradientBoostingFallback"

    def _prepare_features(self, df: pd.DataFrame):
        y = df["label"].astype(int)

        X = df.drop(
            columns=[
                "customer_id",
                "label",
                "customer_age",
                "annual_income"
            ],
            errors="ignore"
        )

        X = pd.get_dummies(
            X,
            columns=[
                "life_event_type",
                "segment",
                "risk_profile"
            ],
            dummy_na=True
        )

        X = X.fillna(0)

        X.columns = [
            self._clean_column_name(column)
            for column in X.columns
        ]

        return X, y

    def _evaluate(self, model, X_eval, y_eval):
        predictions = model.predict(X_eval)

        metrics = {
            "accuracy": accuracy_score(y_eval, predictions),
            "precision": precision_score(y_eval, predictions, zero_division=0),
            "recall": recall_score(y_eval, predictions, zero_division=0)
        }

        if hasattr(model, "predict_proba") and len(set(y_eval)) > 1:
            probabilities = model.predict_proba(X_eval)[:, 1]
            metrics["auc"] = roc_auc_score(y_eval, probabilities)
        else:
            metrics["auc"] = None

        return metrics

    def _get_feature_importance(self, model, X: pd.DataFrame):
        feature_importance = {}

        if hasattr(model, "feature_importances_"):
            feature_importance = dict(
                sorted(
                    zip(X.columns, model.feature_importances_),
                    key=lambda item: item[1],
                    reverse=True
                )
            )

        return feature_importance

    def _safe_name(self, value: str) -> str:
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_")

    def _clean_column_name(self, column_name: str) -> str:
        column_name = str(column_name)
        column_name = re.sub(r"[^A-Za-z0-9_]+", "_", column_name)
        return column_name.strip("_")


if __name__ == "__main__":
    trainer = PerEventModelTrainer()
    trainer.train_all()