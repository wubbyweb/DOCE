import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from sqlalchemy.orm import Session

from doce.agents.orchestrator import OrchestratorAgent, process_invoice_async
from doce.database.models import Invoice, AuditLog


@pytest.mark.asyncio
@patch('doce.agents.invoice_processor.InvoiceProcessingAgent.process_invoice')
@patch('doce.agents.contract_retriever.ContractRetrievalAgent.retrieve_contract')
@patch('doce.agents.validation.ValidationAgent.validate_invoice')
@patch('doce.agents.workflow.WorkflowAgent.process_validation_result')
async def test_process_invoice_success(
    mock_workflow, mock_validation, mock_contract, mock_invoice_process, 
    test_db, mock_kernel
):
    # Set up mocks
    mock_invoice_process.return_value = {
        "vendor_name": "Acme Corp",
        "invoice_number": "INV-001",
        "total_amount": 1250.00
    }
    
    mock_contract.return_value = {
        "contract_id": 1,
        "contract_path": "/test/contracts/acme.pdf",
        "vendor_name": "Acme Corp"
    }
    
    mock_validation.return_value = {
        "is_valid": True,
        "discrepancies": [],
        "summary": "Invoice matches contract terms"
    }
    
    mock_workflow.return_value = {
        "invoice_id": 1,
        "action": "AutoApprove",
        "reason": "Invoice is valid and under threshold",
        "is_valid": True,
        "discrepancies": []
    }
    
    # Get a database session
    db = next(override_get_db())
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent(kernel=mock_kernel, db=db)
    
    # Process an invoice
    result = await orchestrator.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert result["action"] == "AutoApprove"
    assert result["is_valid"] is True
    
    # Verify that all agent methods were called
    mock_invoice_process.assert_called_once()
    mock_contract.assert_called_once_with("Acme Corp")
    mock_validation.assert_called_once()
    mock_workflow.assert_called_once()
    
    # Verify that the invoice status was updated
    invoice = db.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice is not None
    
    # Verify that audit logs were created
    audit_logs = db.query(AuditLog).filter(AuditLog.invoice_id == 1).all()
    assert len(audit_logs) > 0


@pytest.mark.asyncio
@patch('doce.agents.invoice_processor.InvoiceProcessingAgent.process_invoice')
async def test_process_invoice_error_in_processing(
    mock_invoice_process, test_db, mock_kernel
):
    # Set up mock to return an error
    mock_invoice_process.return_value = {
        "error": "Failed to extract data from invoice"
    }
    
    # Get a database session
    db = next(override_get_db())
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent(kernel=mock_kernel, db=db)
    
    # Process an invoice
    result = await orchestrator.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    
    # Verify that only the invoice processing agent was called
    mock_invoice_process.assert_called_once()
    
    # Verify that the invoice status was updated to Error
    invoice = db.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice is not None
    assert invoice.status == "Error"
    
    # Verify that an error audit log was created
    audit_logs = db.query(AuditLog).filter(
        AuditLog.invoice_id == 1,
        AuditLog.action == "Processing Error"
    ).all()
    assert len(audit_logs) > 0


@pytest.mark.asyncio
@patch('doce.agents.invoice_processor.InvoiceProcessingAgent.process_invoice')
@patch('doce.agents.contract_retriever.ContractRetrievalAgent.retrieve_contract')
async def test_process_invoice_no_vendor_name(
    mock_contract, mock_invoice_process, test_db, mock_kernel
):
    # Set up mock to return data without vendor name
    mock_invoice_process.return_value = {
        "invoice_number": "INV-001",
        "total_amount": 1250.00
        # No vendor_name
    }
    
    # Get a database session
    db = next(override_get_db())
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent(kernel=mock_kernel, db=db)
    
    # Process an invoice
    result = await orchestrator.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Vendor name not found" in result["error"]
    
    # Verify that the contract retrieval agent was not called
    mock_contract.assert_not_called()
    
    # Verify that the invoice status was updated to Error
    invoice = db.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice is not None
    assert invoice.status == "Error"


@pytest.mark.asyncio
@patch('doce.agents.invoice_processor.InvoiceProcessingAgent.process_invoice')
@patch('doce.agents.contract_retriever.ContractRetrievalAgent.retrieve_contract')
async def test_process_invoice_contract_not_found(
    mock_contract, mock_invoice_process, test_db, mock_kernel
):
    # Set up mocks
    mock_invoice_process.return_value = {
        "vendor_name": "Unknown Vendor",
        "invoice_number": "INV-001",
        "total_amount": 1250.00
    }
    
    mock_contract.return_value = {
        "error": "No contract found for vendor: Unknown Vendor",
        "vendor_name": "Unknown Vendor"
    }
    
    # Get a database session
    db = next(override_get_db())
    
    # Create orchestrator agent
    orchestrator = OrchestratorAgent(kernel=mock_kernel, db=db)
    
    # Process an invoice
    result = await orchestrator.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "No contract found" in result["error"]
    
    # Verify that the invoice status was updated to Error
    invoice = db.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice is not None
    assert invoice.status == "Error"


@pytest.mark.asyncio
@patch('doce.agents.orchestrator.OrchestratorAgent.process_invoice')
@patch('doce.agents.orchestrator.Kernel')
async def test_process_invoice_async(mock_kernel_class, mock_process_invoice, test_db):
    # Set up mocks
    mock_kernel_instance = MagicMock()
    mock_kernel_class.return_value = mock_kernel_instance
    mock_process_invoice.return_value = {"status": "success"}
    
    # Get a database session
    db = next(override_get_db())
    
    # Call the async function
    await process_invoice_async(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf",
        db=db
    )
    
    # Verify that the kernel was created and configured
    mock_kernel_class.assert_called_once()
    mock_kernel_instance.add_azure_openai_chat_completion_service.assert_called_once()
    
    # Verify that process_invoice was called
    mock_process_invoice.assert_called_once_with(1, "/test/invoices/invoice1.pdf")


@pytest.mark.asyncio
async def test_process_invoice_exception_handling(test_db, mock_kernel):
    # Get a database session
    db = next(override_get_db())
    
    # Create orchestrator agent with a mock that raises an exception
    orchestrator = OrchestratorAgent(kernel=mock_kernel, db=db)
    
    # Mock the invoice_processor to raise an exception
    orchestrator.invoice_processor.process_invoice = AsyncMock(
        side_effect=Exception("Test exception")
    )
    
    # Process an invoice
    result = await orchestrator.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Test exception" in result["error"]
    
    # Verify that the invoice status was updated to Error
    invoice = db.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice is not None
    assert invoice.status == "Error"
    
    # Verify that an error audit log was created
    audit_logs = db.query(AuditLog).filter(
        AuditLog.invoice_id == 1,
        AuditLog.action == "Processing Error"
    ).all()
    assert len(audit_logs) > 0


# Import the override_get_db function from conftest.py
from doce.tests.conftest import override_get_db