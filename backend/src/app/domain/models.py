from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from src.app.core.database import Base

class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False, default="default")
    user_request = Column(Text, nullable=False)
    test_type = Column(String, nullable=True)
    status = Column(String, default="PENDING")
    generated_code = Column(Text, nullable=True)
    test_plan = Column(Text, nullable=True)
    
    execution_status = Column(String, nullable=True)
    report_url = Column(String, nullable=True)
    execution_logs = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
