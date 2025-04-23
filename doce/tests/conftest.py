import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock
import os
import json

from doce.database.database import Base, get_db
from doce.database.models import User, Invoice, Contract, AuditLog
from doce.api.auth import get_password_hash
from doce.main import app
from doce.config import settings

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
    
    # Create a regular user
    regular_user = User(
        name="Regular User",
        email="regular@example.com",
        hashed_password=get_password_hash("regularpassword"),
        role="user"
    )
    db.add(regular_user)
    
    # Create some test contracts
    test_contracts = [
        Contract(
            vendor_name="Acme Corp",
            file_path="/test/contracts/acme.pdf",
            start_date="2023-01-01",
            end_date="2023-12-31",
            status="Active"
        ),
        Contract(
            vendor_name="Globex Inc",
            file_path="/test/contracts/globex.pdf",
            start_date="2023-02-15",
            end_date="2024-02-14",
            status="Active"
        ),
        Contract(
            vendor_name="Initech",
            file_path="/test/contracts/initech.pdf",
            start_date="2023-03-10",
            end_date="2024-03-09",
            status="Active"
        )
    ]
    
    for contract in test_contracts:
        db.add(contract)
    
    db.commit()
    
    # Create some test invoices
    test_invoices = [
        Invoice(
            file_name="invoice1.pdf",
            file_path="/test/invoices/invoice1.pdf",
            status="Validated",
            vendor_name="Acme Corp",
            invoice_number="INV-001",
            invoice_date="2023-10-15",
            total_amount=1250.00,
            extracted_data={"vendor_name": "Acme Corp", "invoice_number": "INV-001", "total_amount": 1250.00},
            contract_id=1
        ),
        Invoice(
            file_name="invoice2.pdf",
            file_path="/test/invoices/invoice2.pdf",
            status="Flagged",
            vendor_name="Globex Inc",
            invoice_number="INV-2023-42",
            invoice_date="2023-10-14",
            total_amount=3750.50,
            extracted_data={"vendor_name": "Globex Inc", "invoice_number": "INV-2023-42", "total_amount": 3750.50},
            flagged_discrepancies=[{"type": "price_mismatch", "description": "Price mismatch for item X", "severity": "high"}],
            contract_id=2
        ),
        Invoice(
            file_name="invoice3.pdf",
            file_path="/test/invoices/invoice3.pdf",
            status="Pending Approval",
            vendor_name="Initech",
            invoice_number="IN-789456",
            invoice_date="2023-10-13",
            total_amount=950.25,
            extracted_data={"vendor_name": "Initech", "invoice_number": "IN-789456", "total_amount": 950.25},
            contract_id=3
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
def admin_token(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


@pytest.fixture
def user_token(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "regular@example.com",
            "password": "regularpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


@pytest.fixture
def mock_kernel():
    # Create a mock kernel
    mock = MagicMock()
    
    # Mock the create_function_from_prompt method
    mock.create_function_from_prompt.return_value = MagicMock()
    
    return mock


@pytest.fixture
def mock_google_vision():
    with patch('doce.plugins.google_vision_plugin.vision') as mock:
        # Mock the ImageAnnotatorClient
        mock_client = MagicMock()
        mock.ImageAnnotatorClient.return_value = mock_client
        
        # Mock the text detection response
        mock_response = MagicMock()
        mock_text = MagicMock()
        mock_text.description = "Mocked OCR text"
        mock_response.text_annotations = [mock_text]
        mock_client.text_detection.return_value = mock_response
        
        yield mock


@pytest.fixture
def sample_invoice_file(tmp_path):
    # Create a sample invoice file for testing
    invoice_content = "Sample invoice content for testing"
    file_path = tmp_path / "test_invoice.pdf"
    with open(file_path, "w") as f:
        f.write(invoice_content)
    return str(file_path)


@pytest.fixture
def sample_contract_file(tmp_path):
    # Create a sample contract file for testing
    contract_content = "Sample contract content for testing"
    file_path = tmp_path / "test_contract.pdf"
    with open(file_path, "w") as f:
        f.write(contract_content)
    return str(file_path)