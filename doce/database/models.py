from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # e.g., "AP Clerk", "Manager"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    approved_invoices = relationship("Invoice", back_populates="approved_by")


class Invoice(Base):
    """Invoice model to store invoice data and status."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String)  # Received, Processing, OCRd, Validated, Flagged, Approved, Rejected
    vendor_name = Column(String, index=True)
    invoice_number = Column(String, index=True)
    invoice_date = Column(DateTime)
    total_amount = Column(Float)
    extracted_data = Column(JSON)  # JSON field to store structured invoice data
    flagged_discrepancies = Column(JSON)  # JSON field to store discrepancies
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    approved_by = relationship("User", back_populates="approved_invoices")
    audit_logs = relationship("AuditLog", back_populates="invoice")
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    contract = relationship("Contract", back_populates="invoices")


class Contract(Base):
    """Contract model to store contract metadata."""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, index=True)
    file_path = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    key_terms_summary = Column(JSON, nullable=True)  # Optional JSON field for key terms
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    invoices = relationship("Invoice", back_populates="contract")


class AuditLog(Base):
    """Audit log model to track actions on invoices."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    action = Column(String)  # e.g., "Uploaded", "OCR Started", "Validation Failed", "Approved"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    details = Column(Text, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


class WorkflowRule(Base):
    """Workflow rule model to define conditions and actions for invoice processing."""
    __tablename__ = "workflow_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    condition = Column(String)  # e.g., "Amount > 1000", "IsFlagged"
    action = Column(String)  # e.g., "RequireManagerApproval"
    priority = Column(Integer, default=0)  # Higher priority rules are evaluated first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())