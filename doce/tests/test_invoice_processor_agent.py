import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

from doce.agents.invoice_processor import InvoiceProcessingAgent


@pytest.fixture
def mock_google_vision_plugin():
    plugin = MagicMock()
    plugin.extract_text.return_value = """
    INVOICE
    
    Acme Corporation
    123 Main Street
    Anytown, CA 12345
    
    Invoice #: INV-2023-001
    Date: 10/15/2023
    
    Bill To:
    DOCE Inc.
    456 Business Ave
    Enterprise, CA 54321
    
    Item                  Quantity    Unit Price    Total
    ---------------------------------------------------------
    Widget A              5           $100.00       $500.00
    Widget B              2           $250.00       $500.00
    Premium Support       1           $300.00       $300.00
    ---------------------------------------------------------
                                      Subtotal:     $1,300.00
                                      Tax (8%):     $104.00
                                      Total:        $1,404.00
    
    Payment Terms: Net 30
    Due Date: 11/14/2023
    
    Thank you for your business!
    """
    return plugin


@pytest.fixture
def mock_nlp_plugin():
    plugin = MagicMock()
    
    # Mock the extract_invoice_data method
    expected_data = {
        "vendor_name": "Acme Corporation",
        "invoice_number": "INV-2023-001",
        "invoice_date": "2023-10-15",
        "total_amount": 1404.00,
        "line_items": [
            {
                "description": "Widget A",
                "quantity": 5,
                "unit_price": 100.00,
                "total": 500.00
            },
            {
                "description": "Widget B",
                "quantity": 2,
                "unit_price": 250.00,
                "total": 500.00
            },
            {
                "description": "Premium Support",
                "quantity": 1,
                "unit_price": 300.00,
                "total": 300.00
            }
        ]
    }
    
    plugin.extract_invoice_data = AsyncMock(return_value=json.dumps(expected_data))
    
    return plugin


@pytest.fixture
def mock_database_plugin():
    plugin = MagicMock()
    
    # Mock the add_audit_log method
    plugin.add_audit_log.return_value = json.dumps({"id": 1, "invoice_id": 1, "action": "Test Action"})
    
    # Mock the update_invoice method
    plugin.update_invoice.return_value = json.dumps({"id": 1, "status": "OCRd"})
    
    return plugin


@pytest.mark.asyncio
async def test_process_invoice_success(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert result["vendor_name"] == "Acme Corporation"
    assert result["invoice_number"] == "INV-2023-001"
    assert result["total_amount"] == 1404.00
    
    # Verify that the plugins were called
    mock_google_vision_plugin.extract_text.assert_called_once_with("/test/invoices/invoice1.pdf")
    mock_nlp_plugin.extract_invoice_data.assert_called_once()
    
    # Verify that audit logs were added
    assert mock_database_plugin.add_audit_log.call_count == 3
    
    # Verify that the invoice was updated
    mock_database_plugin.update_invoice.assert_called_once()
    update_data = json.loads(mock_database_plugin.update_invoice.call_args[0][1])
    assert update_data["vendor_name"] == "Acme Corporation"
    assert update_data["invoice_number"] == "INV-2023-001"
    assert update_data["status"] == "OCRd"


@pytest.mark.asyncio
async def test_process_invoice_ocr_error(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock OCR to return an error
    mock_google_vision_plugin.extract_text.return_value = "Error extracting text: Test error"
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Error extracting text" in result["error"]
    
    # Verify that the plugins were called
    mock_google_vision_plugin.extract_text.assert_called_once_with("/test/invoices/invoice1.pdf")
    mock_nlp_plugin.extract_invoice_data.assert_not_called()
    
    # Verify that an error audit log was added
    mock_database_plugin.add_audit_log.assert_called_once()
    assert "Error" in mock_database_plugin.add_audit_log.call_args[1]["action"]


@pytest.mark.asyncio
async def test_process_invoice_no_text_extracted(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock OCR to return empty text
    mock_google_vision_plugin.extract_text.return_value = ""
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "No text extracted" in result["error"]
    
    # Verify that the plugins were called
    mock_google_vision_plugin.extract_text.assert_called_once_with("/test/invoices/invoice1.pdf")
    mock_nlp_plugin.extract_invoice_data.assert_not_called()


@pytest.mark.asyncio
async def test_process_invoice_nlp_error(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock NLP to return an error
    mock_nlp_plugin.extract_invoice_data = AsyncMock(
        return_value=json.dumps({"error": "Failed to extract data"})
    )
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to extract data" in result["error"]
    
    # Verify that the plugins were called
    mock_google_vision_plugin.extract_text.assert_called_once_with("/test/invoices/invoice1.pdf")
    mock_nlp_plugin.extract_invoice_data.assert_called_once()


@pytest.mark.asyncio
async def test_process_invoice_nlp_json_error(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock NLP to return invalid JSON
    mock_nlp_plugin.extract_invoice_data = AsyncMock(return_value="This is not valid JSON")
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to parse" in result["error"]


@pytest.mark.asyncio
async def test_process_invoice_database_error(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to raise an exception
    mock_database_plugin.update_invoice.side_effect = Exception("Database error")
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Database error" in result["error"]


@pytest.mark.asyncio
async def test_process_invoice_exception_handling(
    mock_google_vision_plugin, mock_nlp_plugin, mock_database_plugin, mock_kernel
):
    # Mock OCR to raise an exception
    mock_google_vision_plugin.extract_text.side_effect = Exception("Unexpected error")
    
    # Create the agent
    agent = InvoiceProcessingAgent(
        kernel=mock_kernel,
        google_vision_plugin=mock_google_vision_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process an invoice
    result = await agent.process_invoice(
        invoice_id=1,
        file_path="/test/invoices/invoice1.pdf"
    )
    
    # Verify the result
    assert "error" in result
    assert "Unexpected error" in result["error"]
    
    # Verify that an error audit log was added
    mock_database_plugin.add_audit_log.assert_called_once()
    assert "Error" in mock_database_plugin.add_audit_log.call_args[1]["action"]