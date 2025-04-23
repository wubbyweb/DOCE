import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

from doce.agents.contract_retriever import ContractRetrievalAgent


@pytest.fixture
def mock_file_system_plugin():
    plugin = MagicMock()
    
    # Mock the find_contract_by_vendor method
    plugin.find_contract_by_vendor.return_value = "/test/contracts/acme_corp_contract.pdf"
    
    # Mock the read_contract method
    plugin.read_contract.return_value = "Sample contract for Acme Corp"
    
    return plugin


@pytest.fixture
def mock_database_plugin():
    plugin = MagicMock()
    
    # Mock the get_contract_by_vendor method for existing contract
    def get_contract_by_vendor(vendor_name):
        if vendor_name == "Acme Corp":
            return json.dumps({
                "id": 1,
                "vendor_name": "Acme Corp",
                "file_path": "/test/contracts/acme_corp_contract.pdf",
                "status": "Active"
            })
        elif vendor_name == "Unknown Vendor":
            return json.dumps({"error": "Contract not found for vendor: Unknown Vendor"})
        else:
            return json.dumps({"error": "Contract not found"})
    
    plugin.get_contract_by_vendor.side_effect = get_contract_by_vendor
    
    return plugin


@pytest.mark.asyncio
async def test_retrieve_contract_from_database(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Acme Corp")
    
    # Verify the result
    assert result["contract_id"] == 1
    assert result["contract_path"] == "/test/contracts/acme_corp_contract.pdf"
    assert result["vendor_name"] == "Acme Corp"
    assert result["source"] == "database"
    
    # Verify that the database plugin was called
    mock_database_plugin.get_contract_by_vendor.assert_called_once_with("Acme Corp")
    
    # Verify that the file system plugin was not called
    mock_file_system_plugin.find_contract_by_vendor.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_contract_from_file_system(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to not find the contract
    mock_database_plugin.get_contract_by_vendor.return_value = json.dumps(
        {"error": "Contract not found for vendor: Globex Inc"}
    )
    
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Globex Inc")
    
    # Verify the result
    assert result["contract_path"] == "/test/contracts/acme_corp_contract.pdf"
    assert result["vendor_name"] == "Globex Inc"
    assert result["source"] == "file_system"
    
    # Verify that the database plugin was called
    mock_database_plugin.get_contract_by_vendor.assert_called_once_with("Globex Inc")
    
    # Verify that the file system plugin was called
    mock_file_system_plugin.find_contract_by_vendor.assert_called_once_with("Globex Inc")


@pytest.mark.asyncio
async def test_retrieve_contract_not_found(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to not find the contract
    mock_database_plugin.get_contract_by_vendor.return_value = json.dumps(
        {"error": "Contract not found for vendor: Unknown Vendor"}
    )
    
    # Mock file system to not find the contract
    mock_file_system_plugin.find_contract_by_vendor.return_value = None
    
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Unknown Vendor")
    
    # Verify the result
    assert "error" in result
    assert "No contract found" in result["error"]
    assert result["vendor_name"] == "Unknown Vendor"
    
    # Verify that both plugins were called
    mock_database_plugin.get_contract_by_vendor.assert_called_once_with("Unknown Vendor")
    mock_file_system_plugin.find_contract_by_vendor.assert_called_once_with("Unknown Vendor")


@pytest.mark.asyncio
async def test_retrieve_contract_database_error(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to raise an exception
    mock_database_plugin.get_contract_by_vendor.side_effect = Exception("Database error")
    
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Acme Corp")
    
    # Verify the result
    assert "error" in result
    assert "Database error" in result["error"]


@pytest.mark.asyncio
async def test_retrieve_contract_file_system_error(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to not find the contract
    mock_database_plugin.get_contract_by_vendor.return_value = json.dumps(
        {"error": "Contract not found for vendor: Acme Corp"}
    )
    
    # Mock file system to raise an exception
    mock_file_system_plugin.find_contract_by_vendor.side_effect = Exception("File system error")
    
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Acme Corp")
    
    # Verify the result
    assert "error" in result
    assert "File system error" in result["error"]


@pytest.mark.asyncio
async def test_retrieve_contract_database_json_error(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to return invalid JSON
    mock_database_plugin.get_contract_by_vendor.return_value = "This is not valid JSON"
    
    # Create the agent
    agent = ContractRetrievalAgent(
        kernel=mock_kernel,
        file_system_plugin=mock_file_system_plugin,
        database_plugin=mock_database_plugin
    )
    
    # Retrieve a contract
    result = await agent.retrieve_contract("Acme Corp")
    
    # Verify the result
    assert result["contract_path"] == "/test/contracts/acme_corp_contract.pdf"
    assert result["vendor_name"] == "Acme Corp"
    assert result["source"] == "file_system"


@pytest.mark.asyncio
async def test_retrieve_contract_file_missing(
    mock_file_system_plugin, mock_database_plugin, mock_kernel
):
    # Mock database to find the contract
    mock_database_plugin.get_contract_by_vendor.return_value = json.dumps({
        "id": 1,
        "vendor_name": "Acme Corp",
        "file_path": "/test/contracts/missing_contract.pdf",
        "status": "Active"
    })
    
    # Mock os.path.exists to return False for the contract path
    with patch('os.path.exists', return_value=False):
        # Create the agent
        agent = ContractRetrievalAgent(
            kernel=mock_kernel,
            file_system_plugin=mock_file_system_plugin,
            database_plugin=mock_database_plugin
        )
        
        # Retrieve a contract
        result = await agent.retrieve_contract("Acme Corp")
        
        # Verify the result
        assert result["contract_path"] == "/test/contracts/acme_corp_contract.pdf"
        assert result["vendor_name"] == "Acme Corp"
        assert result["source"] == "file_system"
        
        # Verify that the file system plugin was called
        mock_file_system_plugin.find_contract_by_vendor.assert_called_once_with("Acme Corp")