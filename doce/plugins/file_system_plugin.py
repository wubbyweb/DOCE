import os
import shutil
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from semantic_kernel.functions import kernel_function, KernelPlugin

class FileSystemPlugin(KernelPlugin):
    """
    Plugin for interacting with the local file system to manage contracts and other files.
    """
    
    def __init__(self, contract_path: str):
        """
        Initialize the File System plugin.
        
        Args:
            contract_path: Base path for contract storage.
        """
        self.contract_path = contract_path
        os.makedirs(contract_path, exist_ok=True)
    
    @kernel_function(
        description="Find a contract by vendor name",
        name="find_contract_by_vendor"
    )
    def find_contract_by_vendor(self, vendor_name: str) -> str:
        """
        Find a contract file by vendor name.
        
        Args:
            vendor_name: Name of the vendor to search for.
            
        Returns:
            Path to the contract file if found, empty string otherwise.
        """
        if not os.path.exists(self.contract_path):
            return ""
        
        # Normalize vendor name for comparison
        vendor_name_lower = vendor_name.lower()
        
        # List all files in the contract directory
        for filename in os.listdir(self.contract_path):
            # Check if the filename contains the vendor name
            if vendor_name_lower in filename.lower():
                return os.path.join(self.contract_path, filename)
        
        return ""
    
    @kernel_function(
        description="Read a contract file",
        name="read_contract"
    )
    def read_contract(self, file_path: str) -> str:
        """
        Read a contract file.
        
        Args:
            file_path: Path to the contract file.
            
        Returns:
            Content of the contract file if it's a text file, or a message indicating it's a binary file.
        """
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        
        # For text files, return the content
        if ext in [".txt", ".md", ".json", ".csv", ".xml", ".html"]:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        
        # For binary files, return a message
        return f"Binary file: {file_path}. Use OCR or other processing methods to extract content."
    
    @kernel_function(
        description="List all contracts",
        name="list_contracts"
    )
    def list_contracts(self) -> str:
        """
        List all contract files.
        
        Returns:
            JSON string containing a list of contract files with metadata.
        """
        if not os.path.exists(self.contract_path):
            return json.dumps([])
        
        contracts = []
        
        for filename in os.listdir(self.contract_path):
            file_path = os.path.join(self.contract_path, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Get file metadata
            stat = os.stat(file_path)
            
            contracts.append({
                "filename": filename,
                "path": file_path,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return json.dumps(contracts, indent=2)
    
    @kernel_function(
        description="Save a contract file",
        name="save_contract"
    )
    def save_contract(self, vendor_name: str, content: str, extension: str = ".txt") -> str:
        """
        Save a contract file.
        
        Args:
            vendor_name: Name of the vendor.
            content: Content to save.
            extension: File extension (default: .txt).
            
        Returns:
            Path to the saved file.
        """
        # Create a safe filename
        safe_vendor_name = "".join(c if c.isalnum() else "_" for c in vendor_name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_vendor_name}_{timestamp}{extension}"
        
        file_path = os.path.join(self.contract_path, filename)
        
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        
        return file_path
    
    @kernel_function(
        description="Save an uploaded contract file",
        name="save_uploaded_contract"
    )
    def save_uploaded_contract(self, source_path: str, vendor_name: str) -> str:
        """
        Save an uploaded contract file.
        
        Args:
            source_path: Path to the source file.
            vendor_name: Name of the vendor.
            
        Returns:
            Path to the saved file.
        """
        if not os.path.exists(source_path):
            return f"Source file not found: {source_path}"
        
        # Create a safe filename
        safe_vendor_name = "".join(c if c.isalnum() else "_" for c in vendor_name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        _, ext = os.path.splitext(source_path)
        filename = f"{safe_vendor_name}_{timestamp}{ext}"
        
        dest_path = os.path.join(self.contract_path, filename)
        
        # Copy the file
        shutil.copy2(source_path, dest_path)
        
        return dest_path