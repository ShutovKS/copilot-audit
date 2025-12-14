from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from src.app.core.database import Base


class TestRun(Base):
	__tablename__ = "test_runs"

	id = Column(Integer, primary_key=True, index=True)
	session_id = Column(String, index=True, nullable=False, default="default")
	user_request = Column(Text, nullable=False)
	test_type = Column(String, nullable=True)
	status = Column(String, default="PENDING")
	generated_code_path = Column(Text, nullable=True)
	test_plan_path = Column(Text, nullable=True)

	execution_status = Column(String, nullable=True)
	report_url = Column(String, nullable=True)
	execution_logs_path = Column(Text, nullable=True)
	hypothesis = Column(Text, nullable=True)

	created_at = Column(DateTime, default=datetime.utcnow)
	updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
	__tablename__ = "notifications"

	id = Column(Integer, primary_key=True, index=True)
	session_id = Column(String, index=True, nullable=False)
	message = Column(Text, nullable=False)
	related_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=True)
	is_read = Column(Boolean, default=False, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)
