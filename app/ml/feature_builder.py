from typing import Dict, List, Any

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.signal import Signal


class FeatureBuilder:
    """
    Converts customer and transaction data into ML-ready features.

    These features can later be passed into LightGBM or XGBoost.
    For now, they are used by the placeholder confidence model.
    """

    CATEGORY_FEATURE_MAP = {
        "Jewellery": "jewellery_spend_total",
        "Event Booking": "event_booking_total",
        "Travel": "travel_spend_total",
        "Lifestyle": "lifestyle_spend_total",
        "Hotel": "hotel_spend_total",
        "Forex": "forex_spend_total",
        "Property Services": "property_services_total",
        "Loan Services": "loan_services_total",
        "Home Furnishing": "home_furnishing_total",
        "Dining": "dining_spend_total",
        "Gifts": "gift_spend_total",
        "Education": "education_spend_total",
        "Exam Fees": "exam_fees_total",
        "Student Accommodation": "student_accommodation_total"
    }

    RISK_PROFILE_ENCODING = {
        "Low": 1,
        "Medium": 2,
        "Medium High": 3,
        "High": 4
    }

    def build_features(
        self,
        customer: Customer,
        transactions: List[Transaction],
        signals: List[Signal],
        event_rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        features = self._default_features()

        features["customer_id"] = customer.customer_id
        features["life_event_type"] = event_rule.get("life_event_type", "Unknown")
        features["segment"] = getattr(customer, "segment", None)
        features["risk_profile"] = getattr(customer, "risk_profile", None)
        features["customer_age"] = customer.age or 0
        features["annual_income"] = float(customer.annual_income or 0)

        risk_profile = getattr(customer, "risk_profile", None)
        features["risk_profile_encoded"] = self._encode_risk_profile(risk_profile)

        features["transaction_count"] = len(transactions)
        features["merchant_category_count"] = len(
            set(transaction.merchant_category for transaction in transactions)
        )

        features["total_transaction_amount"] = sum(
            float(transaction.transaction_amount)
            for transaction in transactions
        )

        self._add_category_spend_features(features, transactions)
        self._add_signal_features(features, signals)
        self._add_event_related_features(features, transactions, event_rule)

        return features

    def _default_features(self) -> Dict[str, Any]:
        features = {
            "customer_id": None,
            "customer_age": 0,
            "annual_income": 0.0,
            "risk_profile_encoded": 0,
            "transaction_count": 0,
            "merchant_category_count": 0,
            "total_transaction_amount": 0.0,
            "matched_signal_count": 0,
            "matched_signal_weight_total": 0.0,
            "total_event_related_spend": 0.0
        }

        for feature_name in self.CATEGORY_FEATURE_MAP.values():
            features[feature_name] = 0.0

        return features

    def _add_category_spend_features(
        self,
        features: Dict[str, Any],
        transactions: List[Transaction]
    ) -> None:
        for transaction in transactions:
            category = transaction.merchant_category
            feature_name = self.CATEGORY_FEATURE_MAP.get(category)

            if feature_name:
                features[feature_name] += float(transaction.transaction_amount)

    def _add_signal_features(
        self,
        features: Dict[str, Any],
        signals: List[Signal]
    ) -> None:
        matched_signals = [
            signal for signal in signals
            if signal.matched
        ]

        features["matched_signal_count"] = len(matched_signals)
        features["matched_signal_weight_total"] = sum(
            float(signal.confidence_contribution)
            for signal in matched_signals
        )

    def _add_event_related_features(
        self,
        features: Dict[str, Any],
        transactions: List[Transaction],
        event_rule: Dict[str, Any]
    ) -> None:
        event_categories = {
            signal_rule["merchant_category"]
            for signal_rule in event_rule.get("transaction_signals", [])
        }

        features["total_event_related_spend"] = sum(
            float(transaction.transaction_amount)
            for transaction in transactions
            if transaction.merchant_category in event_categories
        )

    def _encode_risk_profile(self, risk_profile: str | None) -> int:
        if not risk_profile:
            return 0

        return self.RISK_PROFILE_ENCODING.get(risk_profile, 0)


feature_builder = FeatureBuilder()