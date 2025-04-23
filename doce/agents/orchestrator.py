from typing import Optional, Dict, Any
import json
import os
from sqlalchemy.orm import Session
from semantic_kernel import Kernel

from doce.config import settings
from doce.database.models import Invoice, AuditLog
from doce.plugins import GoogleVisionPlugin, FileSystemPlugin, DatabasePlugin, NLPPlugin, WorkflowRulesPlugin

# Import other agents
from .invoice_processor import InvoiceProcessingAgent
from .contract_retriever import ContractRetrievalAgent
from .validation import ValidationAgent
from .workflow import WorkflowAgent

class OrchestratorAgent:
    """
    Orchestrator Agent that coordinates the invoice validation process.
    """
    
    def __init__(self, kernel: Kernel, db: Session):
        """
        Initialize the Orchestrator Agent.
        
        Args:
            kernel: Semantic Kernel instance.
            db: SQLAlchemy database session.
        """
        self.kernel = kernel
        self.db = db
        
        # Initialize plugins
        self.google_vision_plugin = GoogleVisionPlugin(
            credentials_path=settings.google_vision.credentials_path
        )
        
        self.file_system_plugin = FileSystemPlugin(
            contract_path=settings.file_storage.contract_path
        )
        
        self.database_plugin = DatabasePlugin(db=db)
        
        self.nlp_plugin = NLPPlugin(kernel=kernel)
        
        self.workflow_rules_plugin = WorkflowRulesPlugin()
        
        # Initialize other agents
        self.invoice_processor = InvoiceProcessingAgent(
            kernel=kernel,
            google_vision_plugin=self.google_vision_plugin,
            nlp_plugin=self.nlp_plugin,
            database_plugin=self.database_plugin
        )
        
        self.contract_retriever = ContractRetrievalAgent(
            kernel=kernel,
            file_system_plugin=self.file_system_plugin,
            database_plugin=self.database_plugin
        )
        
        self.validation_agent = ValidationAgent(
            kernel=kernel,
            file_system_plugin=self.file_system_plugin,
            nlp_plugin=self.nlp_plugin,
            database_plugin=self.database_plugin
        )
        
        self.workflow_agent = WorkflowAgent(
            kernel=kernel,
            workflow_rules_plugin=self.workflow_rules_plugin,
            database_plugin=self.database_plugin
        )
    
    async def process_invoice(self, invoice_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process an invoice through the entire validation workflow.
        
        Args:
            invoice_id: ID of the invoice.
            file_path: Path to the invoice file.
            
        Returns:
            Dictionary containing the processing result.
        """
        try:
            # Step 1: Update invoice status to Processing
            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                return {"error": f"Invoice with ID {invoice_id} not found"}
            
            invoice.status = "Processing"
            self.db.commit()
            
            # Create audit log entry
            audit_log = AuditLog(
                invoice_id=invoice_id,
                action="Processing Started",
                details="Invoice processing workflow initiated"
            )
            self.db.add(audit_log)
            self.db.commit()
            
            # Step 2: Process invoice with Invoice Processing Agent
            processing_result = await self.invoice_processor.process_invoice(invoice_id, file_path)
            
            if "error" in processing_result:
                # Update invoice status to Error
                invoice.status = "Error"
                self.db.commit()
                
                # Create audit log entry
                audit_log = AuditLog(
                    invoice_id=invoice_id,
                    action="Processing Error",
                    details=f"Error during invoice processing: {processing_result['error']}"
                )
                self.db.add(audit_log)
                self.db.commit()
                
                return processing_result
            
            # Step 3: Retrieve contract with Contract Retrieval Agent
            vendor_name = processing_result.get("vendor_name")
            if not vendor_name:
                # Update invoice status to Error
                invoice.status = "Error"
                self.db.commit()
                
                # Create audit log entry
                audit_log = AuditLog(
                    invoice_id=invoice_id,
                    action="Processing Error",
                    details="Vendor name not found in extracted invoice data"
                )
                self.db.add(audit_log)
                self.db.commit()
                
                return {"error": "Vendor name not found in extracted invoice data"}
            
            contract_result = await self.contract_retriever.retrieve_contract(vendor_name)
            
            if "error" in contract_result:
                # Update invoice status to Error
                invoice.status = "Error"
                self.db.commit()
                
                # Create audit log entry
                audit_log = AuditLog(
                    invoice_id=invoice_id,
                    action="Processing Error",
                    details=f"Error during contract retrieval: {contract_result['error']}"
                )
                self.db.add(audit_log)
                self.db.commit()
                
                return contract_result
            
            # Step 4: Validate invoice against contract with Validation Agent
            validation_result = await self.validation_agent.validate_invoice(
                invoice_id=invoice_id,
                invoice_data=processing_result,
                contract_path=contract_result.get("contract_path"),
                contract_id=contract_result.get("contract_id")
            )
            
            if "error" in validation_result:
                # Update invoice status to Error
                invoice.status = "Error"
                self.db.commit()
                
                # Create audit log entry
                audit_log = AuditLog(
                    invoice_id=invoice_id,
                    action="Processing Error",
                    details=f"Error during invoice validation: {validation_result['error']}"
                )
                self.db.add(audit_log)
                self.db.commit()
                
                return validation_result
            
            # Step 5: Determine next steps with Workflow Agent
            workflow_result = await self.workflow_agent.process_validation_result(
                invoice_id=invoice_id,
                validation_result=validation_result
            )
            
            return workflow_result
            
        except Exception as e:
            # Handle any unexpected errors
            try:
                # Update invoice status to Error
                invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
                if invoice:
                    invoice.status = "Error"
                    self.db.commit()
                
                # Create audit log entry
                audit_log = AuditLog(
                    invoice_id=invoice_id,
                    action="Processing Error",
                    details=f"Unexpected error during processing: {str(e)}"
                )
                self.db.add(audit_log)
                self.db.commit()
            except:
                pass
            
            return {"error": f"Unexpected error during processing: {str(e)}"}


# Function to process invoice asynchronously (called from API)
async def process_invoice_async(invoice_id: int, file_path: str, db: Session):
    """
    Process an invoice asynchronously.
    
    Args:
        invoice_id: ID of the invoice.
        file_path: Path to the invoice file.
        db: SQLAlchemy database session.
    """
    # Create Semantic Kernel instance
    kernel = Kernel()
    
    # Configure Azure OpenAI
    kernel.add_azure_openai_chat_completion_service(
        service_id="azure-openai",
        deployment_name=settings.azure_openai.deployment_name,
        endpoint=settings.azure_openai.endpoint,
        api_key=settings.azure_openai.api_key
    )
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent(kernel=kernel, db=db)
    
    # Process invoice
    await orchestrator.process_invoice(invoice_id, file_path)