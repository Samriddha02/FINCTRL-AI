from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Dict, Any, Optional


@dataclass
class Customer:
    customer_id: str
    customer_name: str
    email: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Order:
    order_id: str
    case_id: str
    customer_id: str
    order_amount: Decimal
    currency: str
    order_status: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["order_amount"] = f"{self.order_amount:.2f}"
        return d


@dataclass
class Payment:
    payment_id: str
    case_id: str
    order_id: str
    customer_id: str
    amount: Decimal
    currency: str
    payment_method: str
    payment_status: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["amount"] = f"{self.amount:.2f}"
        return d


@dataclass
class Refund:
    refund_id: str
    case_id: str
    payment_id: str
    refund_amount: Decimal
    refund_reason: str
    refund_status: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["refund_amount"] = f"{self.refund_amount:.2f}"
        return d


@dataclass
class Settlement:
    settlement_id: str
    case_id: str
    payment_id: str
    gross_amount: Decimal
    fee_amount: Decimal
    tax_amount: Decimal
    adjustment_amount: Decimal
    net_amount: Decimal
    settlement_status: str
    settlement_date: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["gross_amount"] = f"{self.gross_amount:.2f}"
        d["fee_amount"] = f"{self.fee_amount:.2f}"
        d["tax_amount"] = f"{self.tax_amount:.2f}"
        d["adjustment_amount"] = f"{self.adjustment_amount:.2f}"
        d["net_amount"] = f"{self.net_amount:.2f}"
        return d


@dataclass
class BankTransaction:
    bank_txn_id: str
    case_id: str
    reference_id: str
    amount: Decimal
    transaction_type: str
    description: str
    transaction_date: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["amount"] = f"{self.amount:.2f}"
        return d


@dataclass
class Invoice:
    invoice_id: str
    case_id: str
    order_id: str
    customer_id: str
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    invoice_status: str
    invoice_date: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subtotal"] = f"{self.subtotal:.2f}"
        d["tax_rate"] = f"{self.tax_rate:.4f}"
        d["tax_amount"] = f"{self.tax_amount:.2f}"
        d["total_amount"] = f"{self.total_amount:.2f}"
        return d


@dataclass
class TaxRecord:
    tax_id: str
    case_id: str
    invoice_id: str
    tax_type: str
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    filing_period: str
    recorded_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["taxable_amount"] = f"{self.taxable_amount:.2f}"
        d["tax_rate"] = f"{self.tax_rate:.4f}"
        d["tax_amount"] = f"{self.tax_amount:.2f}"
        return d


@dataclass
class GroundTruth:
    case_id: str
    ground_truth_status: str
    ground_truth_root_cause: str
    ground_truth_expected_amount: Decimal
    ground_truth_actual_amount: Decimal
    ground_truth_should_auto_resolve: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ground_truth_expected_amount"] = f"{self.ground_truth_expected_amount:.2f}"
        d["ground_truth_actual_amount"] = f"{self.ground_truth_actual_amount:.2f}"
        return d
