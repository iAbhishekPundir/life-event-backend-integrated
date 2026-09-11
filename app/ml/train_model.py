from pathlib import Path
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

MODEL_PATH = MODEL_DIR / "life_event_confidence_model.pkl"


class LifeEventModelTrainer:
    """
    Trains a confidence scoring model.

    Preferred model:
    - LightGBM

    Fallback:
    - sklearn GradientBoostingClassifier
    """

    def train(self):
        df = training_dataset_builder.load_training_dataframe()

        if df.empty:
            raise ValueError("Training dataset is empty. Please insert sample data and labels first.")

        if df["label"].nunique() < 2:
            raise ValueError("Training dataset must contain both positive and negative labels.")

        X, y = self._prepare_features(df)

        stratify = y if y.value_counts().min() >= 2 else None

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.3,
            random_state=42,
            stratify=stratify
        )

        if LIGHTGBM_AVAILABLE:
            model = LGBMClassifier(
                n_estimators=50,
                learning_rate=0.05,
                max_depth=3,
                random_state=42
            )
            model_type = "LightGBM"
        else:
            model = GradientBoostingClassifier(
                n_estimators=50,
                learning_rate=0.05,
                max_depth=3,
                random_state=42
            )
            model_type = "GradientBoostingFallback"

        model.fit(X_train, y_train)

        metrics = self._evaluate(model, X_test, y_test)

        artifact = {
            "model": model,
            "model_type": model_type,
            "feature_columns": list(X.columns),
            "metrics": metrics
        }

        joblib.dump(artifact, MODEL_PATH)

        print("Model training completed.")
        print(f"Model type: {model_type}")
        print(f"Model saved at: {MODEL_PATH}")
        print("Metrics:", metrics)

        return artifact

    def _prepare_features(self, df: pd.DataFrame):
        y = df["label"].astype(int)

        drop_columns = [
            "customer_id",
            "label"
        ]

        X = df.drop(columns=drop_columns, errors="ignore")

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

        return X, y

    def _evaluate(self, model, X_test, y_test):
        predictions = model.predict(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, predictions),
            "precision": precision_score(y_test, predictions, zero_division=0),
            "recall": recall_score(y_test, predictions, zero_division=0)
        }

        if hasattr(model, "predict_proba") and len(set(y_test)) > 1:
            probabilities = model.predict_proba(X_test)[:, 1]
            metrics["auc"] = roc_auc_score(y_test, probabilities)
        else:
            metrics["auc"] = None

        return metrics


if __name__ == "__main__":
    trainer = LifeEventModelTrainer()
    trainer.train()