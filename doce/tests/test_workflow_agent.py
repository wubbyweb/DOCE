import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

from doce.agents.workflow import WorkflowAgent


@pytest.fixture
def mock_workflow_rules_plugin():
    plugin = MagicMock()
    
    # Mock the get_next_action method
    auto_approve_result = {
        "action": "AutoApprove",
        "reason": "Invoice is valid and under threshold",
        "rule_name": "Auto-Approve Validated Small Invoices"
    }
    
    manager_approval_result = {
        "action": "RequireManagerApproval",
        "reason": "Invoice is flagged with discrepancies",
        "rule_name": "Manager Review for Flagged Invoices"
    }
    
    review_result = {
        "action": "RequireReview",
        "reason": "Default workflow decision",
        "rule_name": "Default Rule"
    }
    
    def get_next_action(validation_result):
        validation_data = json.loads(validation_result)
        
        if validation_data.get("is_valid", False) and not validation_data.get("discrepancies"):
            # Valid invoice with no discrepancies
            return json.dumps(auto_approve_result)
        elif not validation_data.get("is_valid", True) or validation_data.get("discrepancies"):
            # Invalid invoice or has discrepancies
            return json.dumps(manager_approval_result)
        else:
            # Default case
            return json.dumps(review_result)
    
    plugin.get_next_action = MagicMock(side_effect=get_next_action)
    
    # Mock the set_rules method
    plugin.set_rules = MagicMock()
    
    return plugin


@pytest.fixture
def mock_database_plugin():
    plugin = MagicMock()
    
    # Mock the get_workflow_rules method
    default_rules = [
        {
            "name": "Auto-Approve Validated Small Invoices",
            "condition": "IsValidated AND Amount < 1000",
            "action": "AutoApprove",
            "priority": 100,
            "is_active": True
        },
        {
            "name": "Manager Review for Flagged Invoices",
            "condition": "IsFlagged",
            "action": "RequireManagerApproval",
            "priority": 90,
            "is_active": True
        },
        {
            "name": "Manager Review for Large Invoices",
            "condition": "Amount >= 1000",
            "action": "RequireManagerApproval",
            "priority": 80,
            "is_active": True
        },
        {
            "name": "Default Rule",
            "condition": "true",
            "action": "RequireReview",
            "priority": 0,
            "is_active": True
        }
    ]
    
    plugin.get_workflow_rules.return_value = json.dumps(default_rules)
    
    # Mock the get_invoice method
    valid_invoice = {
        "id": 1,
        "vendor_name": "Acme Corp",
        "invoice_number": "INV-001",
        "total_amount": 500.00,
        "status": "Validated"
    }
    
    flagged_invoice = {
        "id": 2,
        "vendor_name": "Globex Inc",
        "invoice_number": "INV-002",
        "total_amount": 1500.00,
        "status": "Flagged",
        "flagged_discrepancies": [
            {
                "type": "price_mismatch",
                "description": "Price mismatch for Widget A",
                "severity": "high"
            }
        ]
    }
    
    def get_invoice(invoice_id):
        if invoice_id == 1:
            return json.dumps(valid_invoice)
        elif invoice_id == 2:
            return json.dumps(flagged_invoice)
        else:
            return json.dumps({"error": f"Invoice with ID {invoice_id} not found"})
    
    plugin.get_invoice = MagicMock(side_effect=get_invoice)
    
    # Mock the update_invoice method
    plugin.update_invoice.return_value = json.dumps({"id": 1, "status": "Approved"})
    
    # Mock the add_audit_log method
    plugin.add_audit_log.return_value = json.dumps({"id": 1, "invoice_id": 1, "action": "Test Action"})
    
    return plugin


@pytest.fixture
def valid_validation_result():
    return {
        "is_valid": True,
        "discrepancies": [],
        "summary": "The invoice matches the contract terms."
    }


@pytest.fixture
def invalid_validation_result():
    return {
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


@pytest.mark.asyncio
async def test_process_validation_result_auto_approve(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=1,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert result["invoice_id"] == 1
    assert result["action"] == "AutoApprove"
    assert result["is_valid"] is True
    assert len(result["discrepancies"]) == 0
    
    # Verify that the plugins were called
    mock_workflow_rules_plugin.get_next_action.assert_called_once()
    mock_database_plugin.get_invoice.assert_called_once_with(1)
    
    # Verify that the invoice was updated
    mock_database_plugin.update_invoice.assert_called_once()
    update_data = json.loads(mock_database_plugin.update_invoice.call_args[0][1])
    assert update_data["status"] == "Approved"
    
    # Verify that audit logs were added
    assert mock_database_plugin.add_audit_log.call_count >= 2


@pytest.mark.asyncio
async def test_process_validation_result_require_manager_approval(
    mock_workflow_rules_plugin, mock_database_plugin, 
    invalid_validation_result, mock_kernel
):
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=2,
        validation_result=invalid_validation_result
    )
    
    # Verify the result
    assert result["invoice_id"] == 2
    assert result["action"] == "RequireManagerApproval"
    assert result["is_valid"] is False
    assert len(result["discrepancies"]) > 0
    
    # Verify that the invoice was updated
    mock_database_plugin.update_invoice.assert_called_once()
    update_data = json.loads(mock_database_plugin.update_invoice.call_args[0][1])
    assert update_data["status"] == "Pending Approval"


@pytest.mark.asyncio
async def test_process_validation_result_require_review(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Mock workflow rules to return RequireReview
    mock_workflow_rules_plugin.get_next_action.return_value = json.dumps({
        "action": "RequireReview",
        "reason": "Default workflow decision",
        "rule_name": "Default Rule"
    })
    
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=1,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert result["invoice_id"] == 1
    assert result["action"] == "RequireReview"
    
    # Verify that the invoice was updated
    mock_database_plugin.update_invoice.assert_called_once()
    update_data = json.loads(mock_database_plugin.update_invoice.call_args[0][1])
    assert update_data["status"] == "Pending Review"


@pytest.mark.asyncio
async def test_process_validation_result_invoice_not_found(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result for non-existent invoice
    result = await agent.process_validation_result(
        invoice_id=999,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert "error" in result
    assert "not found" in result["error"]
    
    # Verify that the workflow rules plugin was not called
    mock_workflow_rules_plugin.get_next_action.assert_not_called()


@pytest.mark.asyncio
async def test_process_validation_result_invalid_json(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Mock database to return invalid JSON
    mock_database_plugin.get_invoice.return_value = "This is not valid JSON"
    
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=1,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to parse" in result["error"]


@pytest.mark.asyncio
async def test_process_validation_result_workflow_error(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Mock workflow rules to return an error
    mock_workflow_rules_plugin.get_next_action.return_value = json.dumps({
        "error": "Failed to determine next action"
    })
    
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=1,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert "error" in result
    assert "Failed to determine next action" in result["error"]


@pytest.mark.asyncio
async def test_process_validation_result_exception_handling(
    mock_workflow_rules_plugin, mock_database_plugin, 
    valid_validation_result, mock_kernel
):
    # Mock database to raise an exception
    mock_database_plugin.get_invoice.side_effect = Exception("Unexpected error")
    
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Process validation result
    result = await agent.process_validation_result(
        invoice_id=1,
        validation_result=valid_validation_result
    )
    
    # Verify the result
    assert "error" in result
    assert "Unexpected error" in result["error"]
    
    # Verify that an error audit log was added
    mock_database_plugin.add_audit_log.assert_called_once()
    assert "Error" in mock_database_plugin.add_audit_log.call_args[1]["action"]


def test_load_workflow_rules(
    mock_workflow_rules_plugin, mock_database_plugin, mock_kernel
):
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Verify that the rules were loaded
    mock_database_plugin.get_workflow_rules.assert_called_once()
    mock_workflow_rules_plugin.set_rules.assert_called_once()


def test_load_workflow_rules_error(
    mock_workflow_rules_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to raise an exception
    mock_database_plugin.get_workflow_rules.side_effect = Exception("Database error")
    
    # Create the agent
    agent = WorkflowAgent(
        kernel=mock_kernel,
        workflow_rules_plugin=mock_workflow_rules_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Verify that default rules were set
    mock_workflow_rules_plugin.set_rules.assert_called_once()
    rules = mock_workflow_rules_plugin.set_rules.call_args[0][0]
    assert len(rules) > 0
    assert rules[0]["name"] == "Auto-Approve Validated Small Invoices"