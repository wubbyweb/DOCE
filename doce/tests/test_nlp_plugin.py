import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunction

from doce.plugins.nlp_plugin import NLPPlugin

# Sample data for testing
SAMPLE_OCR_TEXT = """
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

SAMPLE_CONTRACT_TEXT = """
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

EXPECTED_INVOICE_DATA = {
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

EXPECTED_CONTRACT_TERMS = {
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

EXPECTED_VALIDATION_RESULT = {
    "is_valid": True,
    "discrepancies": [],
    "summary": "The invoice matches the contract terms."
}


@pytest.fixture
def mock_kernel():
    # Create a mock kernel
    mock_kernel = MagicMock(spec=Kernel)
    
    # Mock the create_function_from_prompt method
    mock_kernel.create_function_from_prompt.return_value = MagicMock(spec=KernelFunction)
    
    # Mock the invoke method to return different results based on the prompt
    async def mock_invoke(function):
        if "extract structured data from invoice OCR text" in str(function):
            return json.dumps(EXPECTED_INVOICE_DATA)
        elif "extract key terms from contract text" in str(function):
            return json.dumps(EXPECTED_CONTRACT_TERMS)
        elif "validates invoice data against contract terms" in str(function):
            return json.dumps(EXPECTED_VALIDATION_RESULT)
        elif "summarize" in str(function):
            return "This is a summary of the text."
        return "Default mock response"
    
    mock_kernel.invoke = AsyncMock(side_effect=mock_invoke)
    
    return mock_kernel


@pytest.mark.asyncio
async def test_extract_invoice_data(mock_kernel):
    # Create the NLP plugin with the mock kernel
    nlp_plugin = NLPPlugin(kernel=mock_kernel)
    
    # Call the extract_invoice_data method
    result = await nlp_plugin.extract_invoice_data(SAMPLE_OCR_TEXT)
    
    # Verify the result
    result_json = json.loads(result)
    assert result_json["vendor_name"] == EXPECTED_INVOICE_DATA["vendor_name"]
    assert result_json["invoice_number"] == EXPECTED_INVOICE_DATA["invoice_number"]
    assert result_json["total_amount"] == EXPECTED_INVOICE_DATA["total_amount"]
    assert len(result_json["line_items"]) == len(EXPECTED_INVOICE_DATA["line_items"])


@pytest.mark.asyncio
async def test_extract_contract_terms(mock_kernel):
    # Create the NLP plugin with the mock kernel
    nlp_plugin = NLPPlugin(kernel=mock_kernel)
    
    # Call the extract_contract_terms method
    result = await nlp_plugin.extract_contract_terms(SAMPLE_CONTRACT_TEXT)
    
    # Verify the result
    result_json = json.loads(result)
    assert result_json["start_date"] == EXPECTED_CONTRACT_TERMS["start_date"]
    assert result_json["end_date"] == EXPECTED_CONTRACT_TERMS["end_date"]
    assert result_json["payment_terms"] == EXPECTED_CONTRACT_TERMS["payment_terms"]
    assert len(result_json["pricing"]) == len(EXPECTED_CONTRACT_TERMS["pricing"])


@pytest.mark.asyncio
async def test_validate_invoice_against_contract(mock_kernel):
    # Create the NLP plugin with the mock kernel
    nlp_plugin = NLPPlugin(kernel=mock_kernel)
    
    # Call the validate_invoice_against_contract method
    result = await nlp_plugin.validate_invoice_against_contract(
        json.dumps(EXPECTED_INVOICE_DATA),
        json.dumps(EXPECTED_CONTRACT_TERMS)
    )
    
    # Verify the result
    result_json = json.loads(result)
    assert "is_valid" in result_json
    assert "discrepancies" in result_json
    assert "summary" in result_json


@pytest.mark.asyncio
async def test_summarize_text(mock_kernel):
    # Create the NLP plugin with the mock kernel
    nlp_plugin = NLPPlugin(kernel=mock_kernel)
    
    # Call the summarize_text method
    result = await nlp_plugin.summarize_text("This is a long text that needs to be summarized.")
    
    # Verify the result
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_extract_invoice_data_error_handling(mock_kernel):
    # Create the NLP plugin with the mock kernel
    nlp_plugin = NLPPlugin(kernel=mock_kernel)
    
    # Mock the invoke method to return an invalid JSON
    mock_kernel.invoke = AsyncMock(return_value="This is not a valid JSON")
    
    # Call the extract_invoice_data method
    result = await nlp_plugin.extract_invoice_data(SAMPLE_OCR_TEXT)
    
    # Verify the result contains an error message
    result_json = json.loads(result)
    assert "error" in result_json