import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

from doce.agents.validation import ValidationAgent


@pytest.fixture
def mock_file_system_plugin():
    plugin = MagicMock()
    
    # Mock the read_contract method
    plugin.read_contract.return_value = """
    SERVICE AGREEMENT
    
    This Service Agreement (the "Agreement") is entered into as of January 1, 2023 (the "Effective Date") 
    by and between Acme Corporation ("Provider") and DOCE Inc. ("Client").
    
    1. SERVICES
    Provider agrees to provide the following services to Client:
    - Supply of Widget A at $100.00 per unit
    - Supply of Widget B at $250.00 per unit
    - Premium Support at $300.00 per month
    
    2. TERM
    The term of this Agreement shall commence on the Effective Date and continue for a period of 
    twelve (12) months, unless earlier terminated in accordance with this Agreement.
    
    3. PAYMENT TERMS
    Client shall pay Provider within thirty (30) days of receipt of invoice.
    
    4. TERMINATION
    Either party may terminate this Agreement with thirty (30) days written notice.
    
    IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.
    
    Acme Corporation                    DOCE Inc.
    ___________________                ___________________
    John Smith, CEO                     Jane Doe, CTO
    """
    
    return plugin


@pytest.fixture
def mock_nlp_plugin():
    plugin = MagicMock()
    
    # Mock the extract_contract_terms method
    contract_terms = {
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "payment_terms": "Net 30",
        "pricing": [
            {
                "description": "Widget A",
                "price": 100.00
            },
            {
                "description": "Widget B",
                "price": 250.00
            },
            {
                "description": "Premium Support",
                "price": 300.00
            }
        ],
        "delivery_terms": None,
        "termination_conditions": "Either party may terminate this Agreement with thirty (30) days written notice.",
        "important_clauses": [
            {
                "title": "Term",
                "description": "12 months from Effective Date"
            }
        ]
    }
    
    plugin.extract_contract_terms = AsyncMock(return_value=json.dumps(contract_terms))
    
    # Mock the validate_invoice_against_contract method
    valid_result = {
        "is_valid": True,
        "discrepancies": [],
        "summary": "The invoice matches the contract terms."
    }
    
    invalid_result = {
        "is_valid": False,
        "discrepancies": [
            {
                "type": "price_mismatch",
                "description": "Price for Widget A is $150.00 in invoice but $100.00 in contract",
                "severity": "high"
            }
        ],
        "summary": "The invoice has discrepancies with the contract terms."
    }
    
    def validate_invoice(invoice_data, contract_terms):
        invoice_data_obj = json.loads(invoice_data)
        
        # Check if there's a price mismatch in the line items
        if "line_items" in invoice_data_obj:
            for item in invoice_data_obj["line_items"]:
                if item["description"] == "Widget A" and item["unit_price"] != 100.00:
                    return json.dumps(invalid_result)
        
        return json.dumps(valid_result)
    
    plugin.validate_invoice_against_contract = AsyncMock(side_effect=validate_invoice)
    
    return plugin


@pytest.fixture
def mock_database_plugin():
    plugin = MagicMock()
    
    # Mock the add_audit_log method
    plugin.add_audit_log.return_value = json.dumps({"id": 1, "invoice_id": 1, "action": "Test Action"})
    
    # Mock the update_invoice method
    plugin.update_invoice.return_value = json.dumps({"id": 1, "status": "Validated"})
    
    # Mock the update_contract_key_terms method
    plugin.update_contract_key_terms.return_value = json.dumps({"id": 1, "key_terms": "{}"})
    
    return plugin


@pytest.fixture
def valid_invoice_data():
    return {
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


@pytest.fixture
def invalid_invoice_data():
    return {
        "vendor_name": "Acme Corporation",
        "invoice_number": "INV-2023-001",
        "invoice_date": "2023-10-15",
        "total_amount": 1554.00,
        "line_items": [
            {
                "description": "Widget A",
                "quantity": 5,
                "unit_price": 150.00,  # Price mismatch
                "total": 750.00
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


@pytest.mark.asyncio
async def test_validate_invoice_valid(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/acme_corp_contract.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert result["is_valid"] is True
    assert len(result["discrepancies"]) == 0
    
    # Verify that the plugins were called
    mock_file_system_plugin.read_contract.assert_called_once_with("/test/contracts/acme_corp_contract.pdf")
    mock_nlp_plugin.extract_contract_terms.assert_called_once()
    mock_nlp_plugin.validate_invoice_against_contract.assert_called_once()
    
    # Verify that the database was updated
    mock_database_plugin.update_contract_key_terms.assert_called_once()
    mock_database_plugin.update_invoice.assert_called_once()
    
    # Verify that audit logs were added
    assert mock_database_plugin.add_audit_log.call_count >= 2


@pytest.mark.asyncio
async def test_validate_invoice_invalid(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    invalid_invoice_data, mock_kernel
):
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=invalid_invoice_data,
        contract_path="/test/contracts/acme_corp_contract.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert result["is_valid"] is False
    assert len(result["discrepancies"]) > 0
    assert "price_mismatch" in result["discrepancies"][0]["type"]
    
    # Verify that the database was updated
    mock_database_plugin.update_invoice.assert_called_once()
    update_data = json.loads(mock_database_plugin.update_invoice.call_args[0][1])
    assert update_data["status"] == "Flagged"
    assert len(update_data["flagged_discrepancies"]) > 0


@pytest.mark.asyncio
async def test_validate_invoice_contract_not_found(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Mock file system to return an error
    mock_file_system_plugin.read_contract.return_value = "File not found: /test/contracts/missing.pdf"
    
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/missing.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert "error" in result
    assert "Contract file not found" in result["error"]
    
    # Verify that NLP plugin was not called
    mock_nlp_plugin.extract_contract_terms.assert_not_called()
    mock_nlp_plugin.validate_invoice_against_contract.assert_not_called()


@pytest.mark.asyncio
async def test_validate_invoice_binary_file(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Mock file system to return a binary file error
    mock_file_system_plugin.read_contract.return_value = "Binary file: /test/contracts/binary.pdf"
    
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/binary.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert "error" in result
    assert "Binary file" in result["error"]


@pytest.mark.asyncio
async def test_validate_invoice_extract_terms_error(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Mock NLP plugin to return an error
    mock_nlp_plugin.extract_contract_terms = AsyncMock(
        return_value=json.dumps({"error": "Failed to extract contract terms"})
    )
    
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/acme_corp_contract.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to extract contract terms" in result["error"]


@pytest.mark.asyncio
async def test_validate_invoice_validation_error(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Mock NLP plugin to return an error during validation
    mock_nlp_plugin.validate_invoice_against_contract = AsyncMock(
        return_value=json.dumps({"error": "Failed to validate invoice"})
    )
    
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/acme_corp_contract.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to validate invoice" in result["error"]


@pytest.mark.asyncio
async def test_validate_invoice_exception_handling(
    mock_file_system_plugin, mock_nlp_plugin, mock_database_plugin, 
    valid_invoice_data, mock_kernel
):
    # Mock file system to raise an exception
    mock_file_system_plugin.read_contract.side_effect = Exception("Unexpected error")
    
    # Create the agent
    agent = ValidationAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        nlp_plugin=mock_nlp_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Validate an invoice
    result = await agent.validate_invoice(
        invoice_id=1,
        invoice_data=valid_invoice_data,
        contract_path="/test/contracts/acme_corp_contract.pdf",
        contract_id=1
    )
    
    # Verify the result
    assert "error" in result
    assert "Unexpected error" in result["error"]
    
    # Verify that an error audit log was added
    mock_database_plugin.add_audit_log.assert_called_once()
    assert "Error" in mock_database_plugin.add_audit_log.call_args[1]["action"]