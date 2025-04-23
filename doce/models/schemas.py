from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field


# User schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class User(UserInDB):
    pass


# Invoice schemas
class InvoiceBase(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    total_amount: Optional[float] = None


class InvoiceCreate(InvoiceBase):
    file_name: str


class InvoiceUpdate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    flagged_discrepancies: Optional[Dict[str, Any]] = None
    contract_id: Optional[int] = None


class InvoiceInDB(InvoiceBase):
    id: int
    file_name: str
    upload_timestamp: datetime
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    flagged_discrepancies: Optional[Dict[str, Any]] = None
    approved_by_id: Optional[int] = None
    approval_timestamp: Optional[datetime] = None
    contract_id: Optional[int] = None

    class Config:
        orm_mode = True


class Invoice(InvoiceInDB):
    pass


# Contract schemas
class ContractBase(BaseModel):
    vendor_name: str
    file_path: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    key_terms_summary: Optional[Dict[str, Any]] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    vendor_name: Optional[str] = None
    file_path: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    key_terms_summary: Optional[Dict[str, Any]] = None


class ContractInDB(ContractBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Contract(ContractInDB):
    pass


# AuditLog schemas
class AuditLogBase(BaseModel):
    invoice_id: int
    action: str
    user_id: Optional[int] = None
    details: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogInDB(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True


class AuditLog(AuditLogInDB):
    pass


# WorkflowRule schemas
class WorkflowRuleBase(BaseModel):
    name: str
    condition: str
    action: str
    priority: int = 0
    is_active: bool = True


class WorkflowRuleCreate(WorkflowRuleBase):
    pass


class WorkflowRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[str] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class WorkflowRuleInDB(WorkflowRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class WorkflowRule(WorkflowRuleInDB):
    pass


# Token schemas for authentication
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# Invoice processing schemas
class InvoiceProcessingResult(BaseModel):
    invoice_id: int
    status: str
    message: str
    extracted_data: Optional[Dict[str, Any]] = None
    flagged_discrepancies: Optional[Dict[str, Any]] = None


# Validation schemas
class ValidationResult(BaseModel):
    is_valid: bool
    discrepancies: List[Dict[str, Any]] = []
    message: str