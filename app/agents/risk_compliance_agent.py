from typing import List

from app.models.transaction import TransactionEvaluationRequest
from app.models.life_event import LifeEventInsight
from app.models.recommendation import Recommendation
from app.models.compliance import ComplianceResult


class RiskComplianceAgent:
    """
    Validates recommendations before they can move forward.

    Checks:
    - KYC status.
    - Nominee availability.
    - Joint account eligibility.
    - Communication consent.
    - Regulatory disclosures.
    - Product suitability.
    """

    def validate(
        self,
        request: TransactionEvaluationRequest,
        life_event: LifeEventInsight,
        recommendations: List[Recommendation]
    ) -> ComplianceResult:
        blocked_reasons: List[str] = []
        regulatory_disclosures: List[str] = []

        kyc_status = self._check_kyc_status(request)
        nominee_status = self._check_nominee_status(request)
        joint_account_eligibility = self._check_joint_account_eligibility(request)
        communication_consent = self._check_communication_consent(request)

        if kyc_status != "Valid":
            blocked_reasons.append("KYC is invalid, missing, or expired")

        if joint_account_eligibility != "Eligible":
            blocked_reasons.append("Joint account eligibility failed")

        if communication_consent != "Valid":
            blocked_reasons.append("Customer communication consent is missing")

        if recommendations:
            regulatory_disclosures.append(
                "Regulatory product disclosures required before customer engagement"
            )

        product_suitability = (
            "Suitable"
            if not blocked_reasons
            else "Review Required"
        )

        final_status = self._determine_final_status(
            blocked_reasons=blocked_reasons,
            nominee_status=nominee_status
        )

        return ComplianceResult(
            customer_id=request.customer.customer_id,
            event_id=life_event.event_id,
            kyc_status=kyc_status,
            nominee_status=nominee_status,
            joint_account_eligibility=joint_account_eligibility,
            regulatory_disclosures=regulatory_disclosures,
            product_suitability=product_suitability,
            communication_consent=communication_consent,
            final_status=final_status,
            blocked_reasons=blocked_reasons
        )

    def _check_kyc_status(self, request: TransactionEvaluationRequest) -> str:
        if request.kyc_status.lower() == "valid":
            return "Valid"

        return "Invalid"

    def _check_nominee_status(self, request: TransactionEvaluationRequest) -> str:
        if request.nominee_available:
            return "Available"

        return "Review Required"

    def _check_joint_account_eligibility(
        self,
        request: TransactionEvaluationRequest
    ) -> str:
        if request.joint_account_eligible:
            return "Eligible"

        return "Not Eligible"

    def _check_communication_consent(
        self,
        request: TransactionEvaluationRequest
    ) -> str:
        if request.communication_consent:
            return "Valid"

        return "Missing"

    def _determine_final_status(
        self,
        blocked_reasons: List[str],
        nominee_status: str
    ) -> str:
        if blocked_reasons:
            return "Blocked"

        if nominee_status == "Review Required":
            return "Review Required"

        return "Compliant"