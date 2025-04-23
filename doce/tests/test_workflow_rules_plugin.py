import pytest
import json
from doce.plugins.workflow_rules_plugin import WorkflowRulesPlugin

# Sample data for testing
SAMPLE_INVOICE_DATA = {
    "id": 1,
    "status": "Validated",
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-2023-001",
    "total_amount": 1500.00,
    "flagged_discrepancies": []
}

SAMPLE_FLAGGED_INVOICE_DATA = {
    "id": 2,
    "status": "Flagged",
    "vendor_name": "Globex Inc",
    "invoice_number": "INV-2023-002",
    "total_amount": 3000.00,
    "flagged_discrepancies": [
        {
            "type": "price_mismatch",
            "description": "Price for Widget A is $150.00 in invoice but $100.00 in contract",
            "severity": "high"
        }
    ]
}

SAMPLE_VALIDATION_RESULT = {
    "is_valid": True,
    "discrepancies": [],
    "summary": "The invoice matches the contract terms."
}

SAMPLE_FLAGGED_VALIDATION_RESULT = {
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

SAMPLE_RULES = [
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


@pytest.fixture
def workflow_rules_plugin():
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    return plugin


def test_evaluate_rules_validated_small_invoice():
    # Create a small validated invoice
    small_invoice = SAMPLE_INVOICE_DATA.copy()
    small_invoice["total_amount"] = 500.00
    
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Evaluate the rules
    result = plugin.evaluate_rules(json.dumps(small_invoice))
    result_json = json.loads(result)
    
    # Verify the result
    assert result_json["action"] == "AutoApprove"
    assert "Auto-Approve Validated Small Invoices" in result_json["reason"]


def test_evaluate_rules_validated_large_invoice():
    # Create a large validated invoice
    large_invoice = SAMPLE_INVOICE_DATA.copy()
    large_invoice["total_amount"] = 1500.00
    
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Evaluate the rules
    result = plugin.evaluate_rules(json.dumps(large_invoice))
    result_json = json.loads(result)
    
    # Verify the result
    assert result_json["action"] == "RequireManagerApproval"
    assert "Manager Review for Large Invoices" in result_json["reason"]


def test_evaluate_rules_flagged_invoice():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Evaluate the rules
    result = plugin.evaluate_rules(json.dumps(SAMPLE_FLAGGED_INVOICE_DATA))
    result_json = json.loads(result)
    
    # Verify the result
    assert result_json["action"] == "RequireManagerApproval"
    assert "Manager Review for Flagged Invoices" in result_json["reason"]


def test_evaluate_rules_no_matching_rule():
    # Create an invoice that doesn't match any specific rule
    invoice = SAMPLE_INVOICE_DATA.copy()
    invoice["status"] = "Processing"  # Not Validated or Flagged
    invoice["total_amount"] = 500.00  # Small amount
    
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Evaluate the rules
    result = plugin.evaluate_rules(json.dumps(invoice))
    result_json = json.loads(result)
    
    # Verify the result (should match the default rule)
    assert result_json["action"] == "RequireReview"
    assert "Default Rule" in result_json["reason"]


def test_evaluate_rules_no_rules():
    # Create the plugin with no rules
    plugin = WorkflowRulesPlugin(rules=[])
    
    # Evaluate the rules
    result = plugin.evaluate_rules(json.dumps(SAMPLE_INVOICE_DATA))
    result_json = json.loads(result)
    
    # Verify the result (should return default action)
    assert result_json["action"] == "RequireReview"
    assert "No workflow rules defined" in result_json["reason"]


def test_evaluate_rules_invalid_json():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Evaluate the rules with invalid JSON
    result = plugin.evaluate_rules("This is not valid JSON")
    result_json = json.loads(result)
    
    # Verify the result
    assert "error" in result_json
    assert result_json["action"] == "RequireReview"


def test_get_next_action_validated():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Get next action for validated result
    result = plugin.get_next_action(json.dumps(SAMPLE_VALIDATION_RESULT))
    result_json = json.loads(result)
    
    # Verify the result
    assert "action" in result_json
    assert "reason" in result_json


def test_get_next_action_flagged():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Get next action for flagged result
    result = plugin.get_next_action(json.dumps(SAMPLE_FLAGGED_VALIDATION_RESULT))
    result_json = json.loads(result)
    
    # Verify the result
    assert result_json["action"] == "RequireManagerApproval"
    assert "Manager Review for Flagged Invoices" in result_json["reason"]


def test_get_next_action_invalid_json():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin(rules=SAMPLE_RULES)
    
    # Get next action with invalid JSON
    result = plugin.get_next_action("This is not valid JSON")
    result_json = json.loads(result)
    
    # Verify the result
    assert "error" in result_json
    assert result_json["action"] == "RequireReview"


def test_create_rule():
    # Create the plugin with empty rules
    plugin = WorkflowRulesPlugin(rules=[])
    
    # Create a new rule
    result = plugin.create_rule(
        name="Test Rule",
        condition="Amount > 500",
        action="RequireReview",
        priority=50
    )
    result_json = json.loads(result)
    
    # Verify the result
    assert result_json["name"] == "Test Rule"
    assert result_json["condition"] == "Amount > 500"
    assert result_json["action"] == "RequireReview"
    assert result_json["priority"] == 50
    assert result_json["is_active"] is True
    
    # Verify the rule was added to the plugin's rules
    assert len(plugin.rules) == 1
    assert plugin.rules[0]["name"] == "Test Rule"


def test_evaluate_complex_condition():
    # Create the plugin with rules
    plugin = WorkflowRulesPlugin()
    
    # Test AND condition
    assert plugin._evaluate_condition(
        "Amount > 1000 AND Vendor == 'Acme Corp'",
        {"total_amount": 1500.00, "vendor_name": "Acme Corp"}
    ) is True
    
    assert plugin._evaluate_condition(
        "Amount > 1000 AND Vendor == 'Acme Corp'",
        {"total_amount": 500.00, "vendor_name": "Acme Corp"}
    ) is False
    
    # Test OR condition
    assert plugin._evaluate_condition(
        "Amount > 1000 OR Vendor == 'Acme Corp'",
        {"total_amount": 500.00, "vendor_name": "Acme Corp"}
    ) is True
    
    assert plugin._evaluate_condition(
        "Amount > 1000 OR Vendor == 'Acme Corp'",
        {"total_amount": 500.00, "vendor_name": "Globex Inc"}
    ) is False