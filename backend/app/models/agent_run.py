from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
import datetime
from app.core.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(String(50), unique=True, nullable=False, index=True)
    case_id = Column(String(50), nullable=False, index=True)
    investigation_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(50), nullable=False, index=True)
    metric_value = Column(Numeric(18, 4), nullable=False)
    recorded_at = Column(DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
