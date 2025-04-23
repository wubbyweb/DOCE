import pytest
import os
import tempfile
import shutil
from pathlib import Path

from doce.plugins.filesystem_plugin import FileSystemPlugin


@pytest.fixture
def temp_contract_dir():
    # Create a temporary directory for contracts
    temp_dir = tempfile.mkdtemp()
    
    # Create some test contract files
    vendor_dirs = ["Acme Corp", "Globex Inc", "Initech"]
    
    for vendor in vendor_dirs:
        # Create vendor directory
        vendor_dir = os.path.join(temp_dir, vendor)
        os.makedirs(vendor_dir, exist_ok=True)
        
        # Create contract files
        contract_file = os.path.join(vendor_dir, f"{vendor.lower().replace(' ', '_')}_contract.pdf")
        with open(contract_file, "w") as f:
            f.write(f"Sample contract for {vendor}")
        
        # Create some additional files
        for i in range(1, 3):
            additional_file = os.path.join(vendor_dir, f"additional_{i}.txt")
            with open(additional_file, "w") as f:
                f.write(f"Additional file {i} for {vendor}")
    
    # Create a directory with mixed case
    mixed_case_dir = os.path.join(temp_dir, "Wayne Enterprises")
    os.makedirs(mixed_case_dir, exist_ok=True)
    contract_file = os.path.join(mixed_case_dir, "wayne_enterprises_contract.pdf")
    with open(contract_file, "w") as f:
        f.write("Sample contract for Wayne Enterprises")
    
    yield temp_dir
    
    # Clean up
    shutil.rmtree(temp_dir)


def test_init_with_contract_path():
    # Test initialization with contract path
    plugin = FileSystemPlugin(contract_path="/path/to/contracts")
    assert plugin.contract_path == "/path/to/contracts"


def test_init_without_contract_path():
    # Test initialization without contract path
    with pytest.raises(ValueError):
        FileSystemPlugin()


def test_find_contract_by_vendor_exact_match(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for Acme Corp
    contract_path = plugin.find_contract_by_vendor("Acme Corp")
    
    # Verify the result
    assert contract_path is not None
    assert os.path.exists(contract_path)
    assert "acme_corp_contract.pdf" in contract_path


def test_find_contract_by_vendor_case_insensitive(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for acme corp (lowercase)
    contract_path = plugin.find_contract_by_vendor("acme corp")
    
    # Verify the result
    assert contract_path is not None
    assert os.path.exists(contract_path)
    assert "acme_corp_contract.pdf" in contract_path


def test_find_contract_by_vendor_partial_match(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for Globex (partial name)
    contract_path = plugin.find_contract_by_vendor("Globex")
    
    # Verify the result
    assert contract_path is not None
    assert os.path.exists(contract_path)
    assert "globex_inc_contract.pdf" in contract_path


def test_find_contract_by_vendor_not_found(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for non-existent vendor
    contract_path = plugin.find_contract_by_vendor("Nonexistent Vendor")
    
    # Verify the result
    assert contract_path is None


def test_find_contract_by_vendor_mixed_case(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for Wayne Enterprises
    contract_path = plugin.find_contract_by_vendor("wayne enterprises")
    
    # Verify the result
    assert contract_path is not None
    assert os.path.exists(contract_path)
    assert "wayne_enterprises_contract.pdf" in contract_path


def test_read_contract_valid_file(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Find contract for Acme Corp
    contract_path = plugin.find_contract_by_vendor("Acme Corp")
    
    # Read the contract
    contract_text = plugin.read_contract(contract_path)
    
    # Verify the result
    assert contract_text == "Sample contract for Acme Corp"


def test_read_contract_nonexistent_file():
    # Create the plugin
    plugin = FileSystemPlugin(contract_path="/tmp")
    
    # Read a non-existent contract
    contract_text = plugin.read_contract("/path/to/nonexistent/contract.pdf")
    
    # Verify the result
    assert "File not found" in contract_text


def test_read_contract_binary_file(temp_contract_dir):
    # Create a binary file
    binary_file = os.path.join(temp_contract_dir, "binary_file.bin")
    with open(binary_file, "wb") as f:
        f.write(b'\x00\x01\x02\x03\x04\x05')
    
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # Read the binary file
    contract_text = plugin.read_contract(binary_file)
    
    # Verify the result
    assert "Binary file" in contract_text


def test_list_contracts(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # List all contracts
    contracts = plugin.list_contracts()
    
    # Verify the result
    assert len(contracts) == 4  # 4 vendors
    
    # Check that each contract has the expected fields
    for contract in contracts:
        assert "vendor_name" in contract
        assert "file_path" in contract
        assert os.path.exists(contract["file_path"])
        assert contract["file_path"].endswith(".pdf")


def test_list_contracts_with_filter(temp_contract_dir):
    # Create the plugin
    plugin = FileSystemPlugin(contract_path=temp_contract_dir)
    
    # List contracts with filter
    contracts = plugin.list_contracts(vendor_filter="Acme")
    
    # Verify the result
    assert len(contracts) == 1
    assert contracts[0]["vendor_name"] == "Acme Corp"


def test_list_contracts_empty_directory():
    # Create an empty temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create the plugin
        plugin = FileSystemPlugin(contract_path=temp_dir)
        
        # List all contracts
        contracts = plugin.list_contracts()
        
        # Verify the result
        assert len(contracts) == 0
    finally:
        # Clean up
        shutil.rmtree(temp_dir)