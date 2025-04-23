import pytest
import os
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from doce.database.database import Base, get_db
from doce.database.models import User, Invoice, AuditLog
from doce.api.auth import get_password_hash
from doce.main import app

# Create a test database in memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables
Base.metadata.create_all(bind=engine)


# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def test_db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test user
    db = TestingSessionLocal()
    hashed_password = get_password_hash("testpassword")
    test_user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hashed_password,
        role="admin"
    )
    db.add(test_user)
    
    # Create some test invoices
    test_invoices = [
        Invoice(
            file_name="invoice1.pdf",
            status="Validated",
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            total_amount=1250.00,
            extracted_data={"vendor_name": "Acme Corp", "invoice_number": "INV-001", "total_amount": 1250.00}
        ),
        Invoice(
            file_name="invoice2.pdf",
            status="Flagged",
            vendor_name="Globex Inc",
            invoice_number="INV-2023-42",
            total_amount=3750.50,
            extracted_data={"vendor_name": "Globex Inc", "invoice_number": "INV-2023-42", "total_amount": 3750.50},
            flagged_discrepancies=[{"type": "price_mismatch", "description": "Price mismatch for item X", "severity": "high"}]
        ),
        Invoice(
            file_name="invoice3.pdf",
            status="Pending Approval",
            vendor_name="Initech",
            invoice_number="IN-789456",
            total_amount=950.25,
            extracted_data={"vendor_name": "Initech", "invoice_number": "IN-789456", "total_amount": 950.25}
        )
    ]
    
    for invoice in test_invoices:
        db.add(invoice)
    
    db.commit()
    
    # Add some audit logs
    for invoice in db.query(Invoice).all():
        audit_log = AuditLog(
            invoice_id=invoice.id,
            action="Created",
            details=f"Test invoice created: {invoice.invoice_number}"
        )
        db.add(audit_log)
    
    db.commit()
    db.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_token(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


def test_get_invoices(auth_token):
    response = client.get(
        "/api/invoices/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["vendor_name"] == "Acme Corp"
    assert data[1]["vendor_name"] == "Globex Inc"
    assert data[2]["vendor_name"] == "Initech"


def test_get_invoices_with_status_filter(auth_token):
    response = client.get(
        "/api/invoices/?status=Flagged",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "Flagged"
    assert data[0]["vendor_name"] == "Globex Inc"


def test_get_invoices_with_vendor_filter(auth_token):
    response = client.get(
        "/api/invoices/?vendor_name=Acme",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["vendor_name"] == "Acme Corp"


def test_get_invoice_by_id(auth_token):
    # First get all invoices to find an ID
    response = client.get(
        "/api/invoices/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    invoices = response.json()
    invoice_id = invoices[0]["id"]
    
    # Now get the specific invoice
    response = client.get(
        f"/api/invoices/{invoice_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert "vendor_name" in data
    assert "invoice_number" in data
    assert "status" in data


def test_get_invoice_not_found(auth_token):
    response = client.get(
        "/api/invoices/9999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_invoice_audit_logs(auth_token):
    # First get all invoices to find an ID
    response = client.get(
        "/api/invoices/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    invoices = response.json()
    invoice_id = invoices[0]["id"]
    
    # Now get the audit logs for this invoice
    response = client.get(
        f"/api/invoices/{invoice_id}/audit-logs",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["invoice_id"] == invoice_id
    assert "action" in data[0]
    assert "details" in data[0]


@patch('doce.agents.orchestrator.process_invoice_async')
def test_approve_invoice(mock_process, auth_token, test_db):
    # Mock the background task
    mock_process.return_value = None
    
    # First get all invoices to find a validated one
    response = client.get(
        "/api/invoices/?status=Validated",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    invoices = response.json()
    invoice_id = invoices[0]["id"]
    
    # Now approve the invoice
    response = client.put(
        f"/api/invoices/{invoice_id}/approve",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert data["status"] == "Approved"
    assert data["approved_by_id"] is not None


@patch('doce.agents.orchestrator.process_invoice_async')
def test_reject_invoice(mock_process, auth_token, test_db):
    # Mock the background task
    mock_process.return_value = None
    
    # First get all invoices to find a flagged one
    response = client.get(
        "/api/invoices/?status=Flagged",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    invoices = response.json()
    invoice_id = invoices[0]["id"]
    
    # Now reject the invoice
    response = client.put(
        f"/api/invoices/{invoice_id}/reject",
        params={"reason": "Test rejection reason"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert data["status"] == "Rejected"