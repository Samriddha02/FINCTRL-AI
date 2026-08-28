from typing import List, Any
from decimal import Decimal
from app.reconciliation.models import EvidenceItem, RuleEvaluation


class EvidenceCollector:
    """Helper class to collect evidence items and rule evaluations for a case."""

    def __init__(self):
        self.evidence: List[EvidenceItem] = []
        self.rule_evaluations: List[RuleEvaluation] = []

    def add_evidence(
        self,
        source: str,
        record_id: str,
        field: str,
        value: Any,
        explanation: str,
    ):
        self.evidence.append(
            EvidenceItem(
                source=source,
                record_id=str(record_id),
                field=field,
                value=str(value),
                explanation=explanation,
            )
        )

    def add_rule_evaluation(
        self,
        rule_name: str,
        status: str,
        expected_val: Any,
        actual_val: Any,
        difference: Any = "0.00",
    ):
        exp_str = f"{expected_val:.2f}" if isinstance(expected_val, Decimal) else str(expected_val)
        act_str = f"{actual_val:.2f}" if isinstance(actual_val, Decimal) else str(actual_val)
        diff_str = f"{difference:.2f}" if isinstance(difference, Decimal) else str(difference)

        self.rule_evaluations.append(
            RuleEvaluation(
                rule_name=rule_name,
                status=status,
                expected_val=exp_str,
                actual_val=act_str,
                difference=diff_str,
            )
        )
