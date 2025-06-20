from sqlalchemy import Column, String, DateTime, Integer, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID 
from uuid import uuid4
from datetime import datetime
from ..utils.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)  
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=True)
    change_data = Column(JSON, nullable=True)  
    created_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(UUID(as_uuid=True), nullable=False) 
    checkbox_value = Column(Boolean, nullable=False)
    inspected_at = Column(DateTime, nullable=False)
    # inspector_id = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(String, nullable=True)    