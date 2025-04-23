from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from sqlalchemy.orm import Session
from semantic_kernel.plugin_definition import kernel_function, KernelPlugin

from doce.database.models import Invoice, Contract, AuditLog, WorkflowRule, User

class DatabasePlugin(KernelPlugin):
    """
    Plugin for interacting with the application database.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Database plugin.
        
        Args:
            db: SQLAlchemy database session.
        """
        self.db = db
    
    # Invoice operations
    
    @kernel_function(
        description="Get invoice by ID",
        name="get_invoice"
    )
    def get_invoice(self, invoice_id: int) -> str:
        """
        Get an invoice by ID.
        
        Args:
            invoice_id: ID of the invoice.
            
        Returns:
            JSON string containing the invoice data.
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            return json.dumps({"error": f"Invoice with ID {invoice_id} not found"})
        
        # Convert to dictionary
        invoice_dict = {
            "id": invoice.id,
            "file_name": invoice.file_name,
            "upload_timestamp": invoice.upload_timestamp.isoformat() if invoice.upload_timestamp else None,
            "status": invoice.status,
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "total_amount": invoice.total_amount,
            "extracted_data": invoice.extracted_data,
            "flagged_discrepancies": invoice.flagged_discrepancies,
            "approved_by_id": invoice.approved_by_id,
            "approval_timestamp": invoice.approval_timestamp.isoformat() if invoice.approval_timestamp else None,
            "contract_id": invoice.contract_id
        }
        
        return json.dumps(invoice_dict, indent=2)
    
    @kernel_function(
        description="Update invoice data",
        name="update_invoice"
    )
    def update_invoice(self, invoice_id: int, update_data: str) -> str:
        """
        Update an invoice.
        
        Args:
            invoice_id: ID of the invoice.
            update_data: JSON string containing the fields to update.
            
        Returns:
            JSON string containing the updated invoice data.
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            return json.dumps({"error": f"Invoice with ID {invoice_id} not found"})
        
        # Parse update data
        try:
            data = json.loads(update_data)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON data"})
        
        # Update fields
        for key, value in data.items():
            if hasattr(invoice, key):
                # Handle date fields
                if key == "invoice_date" and value:
                    try:
                        value = datetime.fromisoformat(value)
                    except ValueError:
                        return json.dumps({"error": f"Invalid date format for {key}"})
                
                setattr(invoice, key, value)
        
        self.db.commit()
        
        # Return updated invoice
        return self.get_invoice(invoice_id)
    
    @kernel_function(
        description="Add audit log entry",
        name="add_audit_log"
    )
    def add_audit_log(self, invoice_id: int, action: str, user_id: Optional[int] = None, details: Optional[str] = None) -> str:
        """
        Add an audit log entry.
        
        Args:
            invoice_id: ID of the invoice.
            action: Action performed.
            user_id: ID of the user who performed the action (optional).
            details: Additional details (optional).
            
        Returns:
            JSON string containing the created audit log entry.
        """
        # Check if invoice exists
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            return json.dumps({"error": f"Invoice with ID {invoice_id} not found"})
        
        # Create audit log entry
        audit_log = AuditLog(
            invoice_id=invoice_id,
            action=action,
            user_id=user_id,
            details=details
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        # Convert to dictionary
        audit_log_dict = {
            "id": audit_log.id,
            "timestamp": audit_log.timestamp.isoformat() if audit_log.timestamp else None,
            "invoice_id": audit_log.invoice_id,
            "action": audit_log.action,
            "user_id": audit_log.user_id,
            "details": audit_log.details
        }
        
        return json.dumps(audit_log_dict, indent=2)
    
    # Contract operations
    
    @kernel_function(
        description="Get contract by vendor name",
        name="get_contract_by_vendor"
    )
    def get_contract_by_vendor(self, vendor_name: str) -> str:
        """
        Get a contract by vendor name.
        
        Args:
            vendor_name: Name of the vendor.
            
        Returns:
            JSON string containing the contract data.
        """
        contract = self.db.query(Contract).filter(Contract.vendor_name.ilike(f"%{vendor_name}%")).first()
        
        if not contract:
            return json.dumps({"error": f"Contract for vendor '{vendor_name}' not found"})
        
        # Convert to dictionary
        contract_dict = {
            "id": contract.id,
            "vendor_name": contract.vendor_name,
            "file_path": contract.file_path,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "key_terms_summary": contract.key_terms_summary,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None
        }
        
        return json.dumps(contract_dict, indent=2)
    
    @kernel_function(
        description="Get contract by ID",
        name="get_contract"
    )
    def get_contract(self, contract_id: int) -> str:
        """
        Get a contract by ID.
        
        Args:
            contract_id: ID of the contract.
            
        Returns:
            JSON string containing the contract data.
        """
        contract = self.db.query(Contract).filter(Contract.id == contract_id).first()
        
        if not contract:
            return json.dumps({"error": f"Contract with ID {contract_id} not found"})
        
        # Convert to dictionary
        contract_dict = {
            "id": contract.id,
            "vendor_name": contract.vendor_name,
            "file_path": contract.file_path,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "key_terms_summary": contract.key_terms_summary,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None
        }
        
        return json.dumps(contract_dict, indent=2)
    
    @kernel_function(
        description="Update contract key terms",
        name="update_contract_key_terms"
    )
    def update_contract_key_terms(self, contract_id: int, key_terms: str) -> str:
        """
        Update a contract's key terms summary.
        
        Args:
            contract_id: ID of the contract.
            key_terms: JSON string containing the key terms.
            
        Returns:
            JSON string containing the updated contract data.
        """
        contract = self.db.query(Contract).filter(Contract.id == contract_id).first()
        
        if not contract:
            return json.dumps({"error": f"Contract with ID {contract_id} not found"})
        
        # Parse key terms
        try:
            terms_data = json.loads(key_terms)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON data for key terms"})
        
        # Update key terms
        contract.key_terms_summary = terms_data
        self.db.commit()
        
        # Return updated contract
        return self.get_contract(contract_id)
    
    # Workflow rule operations
    
    @kernel_function(
        description="Get workflow rules",
        name="get_workflow_rules"
    )
    def get_workflow_rules(self) -> str:
        """
        Get all active workflow rules.
        
        Returns:
            JSON string containing the workflow rules.
        """
        rules = self.db.query(WorkflowRule).filter(WorkflowRule.is_active == True).order_by(
            WorkflowRule.priority.desc()
        ).all()
        
        rules_list = []
        for rule in rules:
            rules_list.append({
                "id": rule.id,
                "name": rule.name,
                "condition": rule.condition,
                "action": rule.action,
                "priority": rule.priority,
                "is_active": rule.is_active
            })
        
        return json.dumps(rules_list, indent=2)