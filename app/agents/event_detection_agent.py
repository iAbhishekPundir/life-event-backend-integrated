from typing import List
from uuid import uuid4

from app.ml.confidence_model import confidence_model
from app.ml.feature_builder import feature_builder
from app.models.life_event import LifeEventInsight
from app.models.signal import Signal
from app.models.transaction import TransactionEvaluationRequest
from app.services.rule_loader_service import RuleLoaderService
from app.llm.insight_generator import insight_generator


class EventDetectionAgent:
    """
    Event detection flow:

    1. Rules identify candidate event.
    2. FeatureBuilder converts customer and transaction data into ML-ready features.
    3. ConfidenceModel calculates placeholder ML confidence score.
    4. Rules validate threshold and actionability.
    """

    def __init__(self):
        self.rule_loader = RuleLoaderService()

    def detect(self, request: TransactionEvaluationRequest) -> LifeEventInsight:
        rules = self.rule_loader.load_life_event_rules()
        candidates: List[LifeEventInsight] = []

        for event_rule in rules.get("life_events", []):
            if not event_rule.get("enabled", False):
                continue

            life_event_type = event_rule["life_event_type"]
            minimum_confidence_score = float(
                event_rule.get("minimum_confidence_score", 0.7)
            )
            estimated_timeline = event_rule.get("estimated_timeline", "Unknown")

            signals: List[Signal] = []
            key_drivers: List[str] = []

            for signal_rule in event_rule.get("transaction_signals", []):
                signal = self._evaluate_signal(signal_rule, request)
                signals.append(signal)

                if signal.matched:
                    key_drivers.append(signal.signal_name)

            features = feature_builder.build_features(
                customer=request.customer,
                transactions=request.transactions,
                signals=signals,
                event_rule=event_rule
            )

            confidence_score , score_source = confidence_model.predict_confidence(
                features=features,
                signals=signals,
                event_rule=event_rule
            )

            actionable = self._validate_actionability(
                confidence_score=confidence_score,
                minimum_confidence_score=minimum_confidence_score,
                request=request,
                event_rule=event_rule,
                signals=signals
            )

            # status = "Actionable" if actionable else "Below Threshold"
            status = self._determine_status(
                confidence_score=confidence_score,
                minimum_confidence_score=minimum_confidence_score,
                event_rule=event_rule,
                signals=signals
            )
            
            actionable = status == "Actionable"

            # The LLM summary is only ever shown for whichever candidate
            # _select_best_candidate ends up returning -- every other
            # candidate's summary is discarded. Generating it here for all
            # (up to 5) candidates meant up to 5 sequential LLM calls per
            # detect() call, most of them wasted. Deferred below to a single
            # call on the winning candidate only.
            candidates.append(
                LifeEventInsight(
                    event_id=f"EVT-{uuid4().hex[:8].upper()}",
                    customer_id=request.customer.customer_id,
                    life_event_type=life_event_type,
                    confidence_score=confidence_score,
                    score_source=score_source,
                    estimated_timeline=estimated_timeline,
                    key_drivers=key_drivers,
                    signals=signals,
                    actionable=actionable,
                    status=status,
                    approval_status=rules.get(
                        "default_approval_status",
                        "Pending Human Approval"
                    ),
                    customer_facing_allowed=rules.get(
                        "default_customer_facing_allowed",
                        False
                    )
                )
            )

        if not candidates:
            return self._no_event_detected(request)

        best_candidate = self._select_best_candidate(candidates)

        insight_payload = insight_generator.generate_summary(
            customer_name=request.customer.name,
            life_event_type=best_candidate.life_event_type,
            confidence_score=best_candidate.confidence_score,
            key_drivers=best_candidate.key_drivers,
            estimated_timeline=best_candidate.estimated_timeline,
            status=best_candidate.status,
            score_source=best_candidate.score_source,
            actionable=best_candidate.actionable
        )
        best_candidate.ai_summary = insight_payload["ai_summary"]
        best_candidate.advisor_talking_points = insight_payload["advisor_talking_points"]

        return best_candidate

    
    def _evaluate_signal(
        self,
        signal_rule: dict,
        request: TransactionEvaluationRequest
    ) -> Signal:
        signal_name = signal_rule["signal_name"]
        expected_merchant_category = signal_rule["merchant_category"].lower()
        minimum_amount = float(signal_rule.get("minimum_amount", 0))
        weight = float(signal_rule.get("weight", 0.0))

        matched = False
        reason = "No matching transaction found"

        for transaction in request.transactions:
            category_match = (
                transaction.merchant_category.lower()
                == expected_merchant_category
            )

            amount_match = float(transaction.transaction_amount) >= minimum_amount

            if category_match and amount_match:
                matched = True
                reason = (
                    f"Matched transaction {transaction.transaction_id}: "
                    f"{transaction.merchant_category} amount "
                    f"{transaction.transaction_amount}"
                )
                break

        return Signal(
            signal_name=signal_name,
            matched=matched,
            source="Transaction Data",
            confidence_contribution=weight if matched else 0.0,
            reason=reason
        )

    def _validate_actionability(
        self,
        confidence_score: float,
        minimum_confidence_score: float,
        request: TransactionEvaluationRequest,
        event_rule: dict,
        signals: List[Signal]
    ) -> bool:
        validation_rules = event_rule.get("validation_rules", {})

        if validation_rules.get("block_if_confidence_below_threshold", True):
            if confidence_score < minimum_confidence_score:
                return False

        minimum_matched_signals = int(event_rule.get("minimum_matched_signals", 1))

        matched_signal_count = len([
            signal for signal in signals
            if signal.matched
        ])

        if matched_signal_count < minimum_matched_signals:
            return False

        if validation_rules.get("requires_consent", False):
            if not request.communication_consent:
                return False

        return True

    def _select_best_candidate(
        self,
        candidates: List[LifeEventInsight]
    ) -> LifeEventInsight:
        actionable_candidates = [
            candidate for candidate in candidates
            if candidate.actionable
        ]

        if actionable_candidates:
            return max(
                actionable_candidates,
                key=lambda candidate: candidate.confidence_score
            )

        return max(
            candidates,
            key=lambda candidate: candidate.confidence_score
        )

    def _no_event_detected(
        self,
        request: TransactionEvaluationRequest
    ) -> LifeEventInsight:
        return LifeEventInsight(
            event_id=f"EVT-{uuid4().hex[:8].upper()}",
            customer_id=request.customer.customer_id,
            life_event_type="Unknown",
            confidence_score=0.0,
            score_source="NOT_APPLICABLE",
            estimated_timeline="Unknown",
            key_drivers=[],
            signals=[],
            actionable=False,
            status="No Event Detected",
            approval_status="Not Required",
            customer_facing_allowed=False
        )
    
    def _determine_status(
        self,
        confidence_score: float,
        minimum_confidence_score: float,
        event_rule: dict,
        signals: list
    ) -> str:
        matched_signal_count = len([
            signal for signal in signals
            if signal.matched
        ])

        minimum_matched_signals = int(event_rule.get("minimum_matched_signals", 1))

        if confidence_score < minimum_confidence_score:
            return "Below Confidence Threshold"

        if matched_signal_count < minimum_matched_signals:
            return "Insufficient Matched Signals"

        return "Actionable"