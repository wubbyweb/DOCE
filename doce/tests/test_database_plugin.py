import pytest
import json
from sqlalchemy.orm import Session

from doce.plugins.database_plugin import DatabasePlugin
from doce.database.models import Invoice, Contract, AuditLog, User
from doce.tests.conftest import override_get_db


@pytest.fixture
def db_session():
    # Get a database session
    return next(override_get_db())


@pytest.fixture
def database_plugin(db_session):
    # Create a database plugin
    return DatabasePlugin(db=db_session)


def test_get_invoice(database_plugin, test_db):
    # Get an invoice
    invoice_json = database_plugin.get_invoice(1)
    invoice = json.loads(invoice_json)
    
    # Verify the result
    assert invoice["id"] == 1
    assert invoice["vendor_name"] == "Acme Corp"
    assert invoice["invoice_number"] == "INV-001"
    assert invoice["status"] == "Validated"


def test_get_invoice_not_found(database_plugin, test_db):
    # Get a non-existent invoice
    invoice_json = database_plugin.get_invoice(999)
    invoice = json.loads(invoice_json)
    
    # Verify the result
    assert "error" in invoice
    assert "not found" in invoice["error"]


def test_update_invoice(database_plugin, test_db, db_session):
    # Update an invoice
    update_data = {
        "status": "Approved",
        "approved_by_id": 1,
        "notes": "Approved by test"
    }
    
    result_json = database_plugin.update_invoice(1, json.dumps(update_data))
    result = json.loads(result_json)
    
    # Verify the result
    assert result["id"] == 1
    assert result["status"] == "Approved"
    assert result["approved_by_id"] == 1
    assert result["notes"] == "Approved by test"
    
    # Verify the database was updated
    invoice = db_session.query(Invoice).filter(Invoice.id == 1).first()
    assert invoice.status == "Approved"
    assert invoice.approved_by_id == 1
    assert invoice.notes == "Approved by test"


def test_update_invoice_not_found(database_plugin, test_db):
    # Update a non-existent invoice
    update_data = {
        "status": "Approved"
    }
    
    result_json = database_plugin.update_invoice(999, json.dumps(update_data))
    result = json.loads(result_json)
    
    # Verify the result
    assert "error" in result
    assert "not found" in result["error"]


def test_update_invoice_invalid_json(database_plugin, test_db):
    # Update an invoice with invalid JSON
    result_json = database_plugin.update_invoice(1, "This is not valid JSON")
    result = json.loads(result_json)
    
    # Verify the result
    assert "error" in result
    assert "Invalid JSON" in result["error"]


def test_get_contract_by_vendor(database_plugin, test_db):
    # Get a contract by vendor name
    contract_json = database_plugin.get_contract_by_vendor("Acme Corp")
    contract = json.loads(contract_json)
    
    # Verify the result
    assert contract["vendor_name"] == "Acme Corp"
    assert contract["status"] == "Active"
    assert "file_path" in contract


def test_get_contract_by_vendor_not_found(database_plugin, test_db):
    # Get a contract for a non-existent vendor
    contract_json = database_plugin.get_contract_by_vendor("Nonexistent Vendor")
    contract = json.loads(contract_json)
    
    # Verify the result
    assert "error" in contract
    assert "not found" in contract["error"]


def test_get_contract_by_vendor_partial_match(database_plugin, test_db):
    # Get a contract by partial vendor name
    contract_json = database_plugin.get_contract_by_vendor("Acme")
    contract = json.loads(contract_json)
    
    # Verify the result
    assert contract["vendor_name"] == "Acme Corp"


def test_update_contract_key_terms(database_plugin, test_db, db_session):
    # Update contract key terms
    key_terms = {
        "payment_terms": "Net 30",
        "pricing": [
            {"item": "Widget A", "price": 100.00},
            {"item": "Widget B", "price": 200.00}
        ]
    }
    
    result_json = database_plugin.update_contract_key_terms(1, json.dumps(key_terms))
    result = json.loads(result_json)
    
    # Verify the result
    assert result["id"] == 1
    assert "key_terms" in result
    
    # Verify the database was updated
    contract = db_session.query(Contract).filter(Contract.id == 1).first()
    assert contract.key_terms is not None
    contract_key_terms = json.loads(contract.key_terms)
    assert contract_key_terms["payment_terms"] == "Net 30"
    assert len(contract_key_terms["pricing"]) == 2


def test_update_contract_key_terms_not_found(database_plugin, test_db):
    # Update key terms for a non-existent contract
    key_terms = {
        "payment_terms": "Net 30"
    }
    
    result_json = database_plugin.update_contract_key_terms(999, json.dumps(key_terms))
    result = json.loads(result_json)
    
    # Verify the result
    assert "error" in result
    assert "not found" in result["error"]


def test_update_contract_key_terms_invalid_json(database_plugin, test_db):
    # Update contract key terms with invalid JSON
    result_json = database_plugin.update_contract_key_terms(1, "This is not valid JSON")
    result = json.loads(result_json)
    
    # Verify the result
    assert "error" in result
    assert "Invalid JSON" in result["error"]


def test_add_audit_log(database_plugin, test_db, db_session):
    # Add an audit log
    result_json = database_plugin.add_audit_log(
        invoice_id=1,
        action="Test Action",
        details="Test details for audit log"
    )
    result = json.loads(result_json)
    
    # Verify the result
    assert result["invoice_id"] == 1
    assert result["action"] == "Test Action"
    assert result["details"] == "Test details for audit log"
    
    # Verify the database was updated
    audit_log = db_session.query(AuditLog).filter(
        AuditLog.invoice_id == 1,
        AuditLog.action == "Test Action"
    ).first()
    assert audit_log is not None
    assert audit_log.details == "Test details for audit log"


def test_add_audit_log_invoice_not_found(database_plugin, test_db):
    # Add an audit log for a non-existent invoice
    result_json = database_plugin.add_audit_log(
        invoice_id=999,
        action="Test Action",
        details="Test details for audit log"
    )
    result = json.loads(result_json)
    
    # Verify the result
    assert "error" in result
    assert "not found" in result["error"]


def test_get_workflow_rules(database_plugin, test_db, db_session):
    # First, add some workflow rules to the database
    from doce.database.models import WorkflowRule
    
    rules = [
        WorkflowRule(
            name="Test Rule 1",
            condition="Amount < 1000",
            action="AutoApprove",
            priority=100,
            is_active=True
        ),
        WorkflowRule(
            name="Test Rule 2",
            condition="IsFlagged",
            action="RequireManagerApproval",
            priority=90,
            is_active=True
        )
    ]
    
    for rule in rules:
        db_session.add(rule)
    
    db_session.commit()
    
    # Get workflow rules
    rules_json = database_plugin.get_workflow_rules()
    rules = json.loads(rules_json)
    
    # Verify the result
    assert len(rules) == 2
    assert rules[0]["name"] == "Test Rule 1"
    assert rules[0]["condition"] == "Amount < 1000"
    assert rules[0]["action"] == "AutoApprove"
    assert rules[1]["name"] == "Test Rule 2"


def test_get_workflow_rules_empty(database_plugin, test_db):
    # Get workflow rules when none exist
    rules_json = database_plugin.get_workflow_rules()
    rules = json.loads(rules_json)
    
    # Verify the result
    assert len(rules) == 0


def test_get_user(database_plugin, test_db):
    # Get a user
    user_json = database_plugin.get_user(1)
    user = json.loads(user_json)
    
    # Verify the result
    assert user["id"] == 1
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"
    assert user["role"] == "admin"
    assert "hashed_password" not in user  # Should not include password


def test_get_user_not_found(database_plugin, test_db):
    # Get a non-existent user
    user_json = database_plugin.get_user(999)
    user = json.loads(user_json)
    
    # Verify the result
    assert "error" in user
    assert "not found" in user["error"]


def test_get_user_by_email(database_plugin, test_db):
    # Get a user by email
    user_json = database_plugin.get_user_by_email("test@example.com")
    user = json.loads(user_json)
    
    # Verify the result
    assert user["id"] == 1
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"


def test_get_user_by_email_not_found(database_plugin, test_db):
    # Get a user with a non-existent email
    user_json = database_plugin.get_user_by_email("nonexistent@example.com")
    user = json.loads(user_json)
    
    # Verify the result
    assert "error" in user
    assert "not found" in user["error"]