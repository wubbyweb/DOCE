from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime

from doce.api.auth import get_current_active_user, check_manager_role
from doce.config import settings
from doce.database import get_db
from doce.database.models import Invoice as InvoiceModel, AuditLog as AuditLogModel, User as UserModel
from doce.models import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceProcessingResult, AuditLogCreate

# This will be imported from the agents module once implemented
from doce.agents.orchestrator import process_invoice_async

router = APIRouter()


@router.post("/", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    background_tasks: BackgroundTasks,
    invoice_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Upload a new invoice file and start processing.
    """
    # Ensure invoice upload directory exists
    os.makedirs(settings.file_storage.invoice_path, exist_ok=True)
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{invoice_file.filename}"
    file_path = os.path.join(settings.file_storage.invoice_path, filename)
    
    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(invoice_file.file, buffer)
    
    # Create invoice record in database with initial status
    db_invoice = InvoiceModel(
        file_name=filename,
        status="Received"
    )
    
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    # Create audit log entry
    audit_log = AuditLogModel(
        invoice_id=db_invoice.id,
        action="Uploaded",
        user_id=current_user.id,
        details=f"Invoice file uploaded: {filename}"
    )
    db.add(audit_log)
    db.commit()
    
    # Start background processing task
    background_tasks.add_task(
        process_invoice_async,
        invoice_id=db_invoice.id,
        file_path=file_path,
        db=db
    )
    
    return db_invoice


@router.get("/", response_model=List[Invoice])
def read_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get all invoices with optional filters.
    """
    query = db.query(InvoiceModel)
    
    if status:
        query = query.filter(InvoiceModel.status == status)
    
    if vendor_name:
        query = query.filter(InvoiceModel.vendor_name.ilike(f"%{vendor_name}%"))
    
    invoices = query.order_by(InvoiceModel.upload_timestamp.desc()).offset(skip).limit(limit).all()
    return invoices


@router.get("/{invoice_id}", response_model=Invoice)
def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get a specific invoice by ID.
    """
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return db_invoice


@router.put("/{invoice_id}/approve", response_model=Invoice)
def approve_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Approve an invoice (manager or admin only).
    """
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if db_invoice.status not in ["Validated", "Flagged"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve invoice with status: {db_invoice.status}"
        )
    
    # Update invoice status
    db_invoice.status = "Approved"
    db_invoice.approved_by_id = current_user.id
    db_invoice.approval_timestamp = datetime.now()
    
    # Create audit log entry
    audit_log = AuditLogModel(
        invoice_id=db_invoice.id,
        action="Approved",
        user_id=current_user.id,
        details=f"Invoice approved by {current_user.name}"
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@router.put("/{invoice_id}/reject", response_model=Invoice)
def reject_invoice(
    invoice_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Reject an invoice with a reason (manager or admin only).
    """
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if db_invoice.status not in ["Validated", "Flagged"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject invoice with status: {db_invoice.status}"
        )
    
    # Update invoice status
    db_invoice.status = "Rejected"
    
    # Create audit log entry
    audit_log = AuditLogModel(
        invoice_id=db_invoice.id,
        action="Rejected",
        user_id=current_user.id,
        details=f"Invoice rejected by {current_user.name}. Reason: {reason}"
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@router.get("/{invoice_id}/audit-logs", response_model=List[AuditLogCreate])
def read_invoice_audit_logs(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get audit logs for a specific invoice.
    """
    # Check if invoice exists
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Get audit logs
    audit_logs = db.query(AuditLogModel).filter(
        AuditLogModel.invoice_id == invoice_id
    ).order_by(AuditLogModel.timestamp.desc()).all()
    
    return audit_logs


@router.post("/{invoice_id}/reprocess", response_model=Invoice)
def reprocess_invoice(
    invoice_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Reprocess an invoice (manager or admin only).
    """
    db_invoice = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Get file path
    file_path = os.path.join(settings.file_storage.invoice_path, db_invoice.file_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice file not found"
        )
    
    # Update invoice status
    db_invoice.status = "Processing"
    
    # Create audit log entry
    audit_log = AuditLogModel(
        invoice_id=db_invoice.id,
        action="Reprocessing",
        user_id=current_user.id,
        details=f"Invoice reprocessing initiated by {current_user.name}"
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(db_invoice)
    
    # Start background processing task
    background_tasks.add_task(
        process_invoice_async,
        invoice_id=db_invoice.id,
        file_path=file_path,
        db=db
    )
    
    return db_invoice