from typing import Any, Dict, List, Tuple

from app.ml.event_model_predictor import event_model_predictor
from app.models.signal import Signal


class ConfidenceModel:
    def predict_confidence(
        self,
        features: Dict[str, Any],
        signals: List[Signal],
        event_rule: Dict[str, Any]
    ) -> Tuple[float, str]:
        event_type = event_rule.get("life_event_type", "Unknown")

        if event_model_predictor.is_model_available(event_type):
            try:
                score = event_model_predictor.predict_confidence(
                    event_type=event_type,
                    features=features
                )
                return score, "ML_MODEL"
            except Exception:
                score = self._placeholder_confidence_score(features, event_rule)
                return score, "PLACEHOLDER_RULE_SCORE"

        score = self._placeholder_confidence_score(features, event_rule)
        return score, "PLACEHOLDER_RULE_SCORE"

    def _placeholder_confidence_score(
        self,
        features: Dict[str, Any],
        event_rule: Dict[str, Any]
    ) -> float:
        base_score = float(features.get("matched_signal_weight_total", 0.0))

        matched_signal_count = int(features.get("matched_signal_count", 0))
        transaction_count = int(features.get("transaction_count", 0))
        merchant_category_count = int(features.get("merchant_category_count", 0))
        event_related_spend = float(features.get("total_event_related_spend", 0.0))
        candidate_threshold = float(event_rule.get("candidate_threshold", 0.0))

        score = base_score

        if matched_signal_count >= 4:
            score += 0.08
        elif matched_signal_count == 3:
            score += 0.06
        elif matched_signal_count == 2:
            score += 0.03

        if transaction_count >= 4:
            score += 0.04
        elif transaction_count >= 3:
            score += 0.03

        if merchant_category_count >= 4:
            score += 0.04
        elif merchant_category_count >= 3:
            score += 0.03

        if event_related_spend >= 5000:
            score += 0.05
        elif event_related_spend >= 3000:
            score += 0.04
        elif event_related_spend >= 1500:
            score += 0.02

        if base_score >= candidate_threshold:
            score += 0.03

        return min(round(score, 2), 1.0)


confidence_model = ConfidenceModel()