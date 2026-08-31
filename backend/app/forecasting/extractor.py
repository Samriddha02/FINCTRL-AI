import datetime
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.models import Payment, Settlement, Refund, Order

logger = logging.getLogger("forecast_extractor")


class HistoricalDailyPoint(BaseModel):
    date_str: str
    inflow: Decimal
    outflow: Decimal
    net: Decimal

    class Config:
        arbitrary_types_allowed = True


class HistoricalCashFlowData(BaseModel):
    start_date_str: str
    end_date_str: str
    as_of_str: str
    daily_series: List[HistoricalDailyPoint]
    total_inflow: Decimal
    total_outflow: Decimal
    total_net: Decimal
    observation_days: int
    missing_settlement_count: int

    class Config:
        arbitrary_types_allowed = True


def extract_historical_cash_flows(
    db: Session,
    as_of_date: datetime.date,
    lookback_days: int = 30
) -> HistoricalCashFlowData:
    """Extracts historical daily cash flows strictly before or on as_of_date using Decimal arithmetic."""
    start_date = as_of_date - datetime.timedelta(days=lookback_days - 1)

    # Initialize daily map for all dates in window
    daily_map: Dict[datetime.date, Dict[str, Decimal]] = {}
    curr_date = start_date
    while curr_date <= as_of_date:
        daily_map[curr_date] = {
            "inflow": Decimal("0.00"),
            "outflow": Decimal("0.00"),
            "net": Decimal("0.00")
        }
        curr_date += datetime.timedelta(days=1)

    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    as_of_dt = datetime.datetime.combine(as_of_date, datetime.time.max)

    # 1. Extract Inflows from Settlements (net_amount)
    settlements = (
        db.query(Settlement)
        .filter(Settlement.settlement_date >= start_date)
        .filter(Settlement.settlement_date <= as_of_date)
        .all()
    )

    settled_payment_ids = set()
    for s in settlements:
        s_date = s.settlement_date
        if s_date in daily_map:
            net_dec = Decimal(str(s.net_amount))
            fee_dec = Decimal(str(s.fee_amount)) + Decimal(str(s.tax_amount))
            
            daily_map[s_date]["inflow"] += net_dec
            daily_map[s_date]["outflow"] += fee_dec
            settled_payment_ids.add(s.payment_id)

    # Count missing settlements for payments captured in lookback window
    payments_in_window = (
        db.query(Payment)
        .filter(Payment.created_at >= start_dt)
        .filter(Payment.created_at <= as_of_dt)
        .all()
    )

    missing_settlement_count = 0
    for p in payments_in_window:
        p_date = p.created_at.date()
        if p.payment_id not in settled_payment_ids:
            missing_settlement_count += 1
            if p_date in daily_map:
                daily_map[p_date]["inflow"] += Decimal(str(p.amount))

    # 2. Extract Outflows from Refunds
    refunds = (
        db.query(Refund)
        .filter(Refund.created_at >= start_dt)
        .filter(Refund.created_at <= as_of_dt)
        .all()
    )

    for r in refunds:
        r_date = r.created_at.date()
        if r_date in daily_map:
            r_amt_dec = Decimal(str(r.refund_amount))
            daily_map[r_date]["outflow"] += r_amt_dec

    # Calculate net for each day and totals
    total_inflow = Decimal("0.00")
    total_outflow = Decimal("0.00")
    total_net = Decimal("0.00")
    daily_series: List[HistoricalDailyPoint] = []

    for d in sorted(daily_map.keys()):
        in_d = daily_map[d]["inflow"]
        out_d = daily_map[d]["outflow"]
        net_d = in_d - out_d
        daily_map[d]["net"] = net_d

        total_inflow += in_d
        total_outflow += out_d
        total_net += net_d

        daily_series.append(HistoricalDailyPoint(
            date_str=d.isoformat(),
            inflow=in_d,
            outflow=out_d,
            net=net_d
        ))

    return HistoricalCashFlowData(
        start_date_str=start_date.isoformat(),
        end_date_str=as_of_date.isoformat(),
        as_of_str=as_of_date.isoformat(),
        daily_series=daily_series,
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        total_net=total_net,
        observation_days=len(daily_series),
        missing_settlement_count=missing_settlement_count
    )
