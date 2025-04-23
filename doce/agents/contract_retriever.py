from typing import Dict, Any
import json
import os
from semantic_kernel import Kernel

from doce.plugins import FileSystemPlugin, DatabasePlugin

class ContractRetrievalAgent:
    """
    Agent for retrieving contracts based on vendor information.
    """
    
    def __init__(
        self,
        kernel: Kernel,
        file_system_plugin: FileSystemPlugin,
        database_plugin: DatabasePlugin
    ):
        """
        Initialize the Contract Retrieval Agent.
        
        Args:
            kernel: Semantic Kernel instance.
            file_system_plugin: File System plugin for accessing contracts.
            database_plugin: Database plugin for accessing contract metadata.
        """
        self.kernel = kernel
        self.file_system_plugin = file_system_plugin
        self.database_plugin = database_plugin
    
    async def retrieve_contract(self, vendor_name: str) -> Dict[str, Any]:
        """
        Retrieve a contract for a vendor.
        
        Args:
            vendor_name: Name of the vendor.
            
        Returns:
            Dictionary containing the contract information.
        """
        try:
            # Step 1: Try to find contract in database
            contract_json = self.database_plugin.get_contract_by_vendor(vendor_name)
            
            try:
                contract_data = json.loads(contract_json)
                
                # If contract found in database
                if "error" not in contract_data:
                    contract_path = contract_data.get("file_path")
                    contract_id = contract_data.get("id")
                    
                    # Verify file exists
                    if contract_path and os.path.exists(contract_path):
                        return {
                            "contract_id": contract_id,
                            "contract_path": contract_path,
                            "vendor_name": contract_data.get("vendor_name"),
                            "source": "database"
                        }
            except json.JSONDecodeError:
                pass
            
            # Step 2: If not found in database or file missing, try file system
            contract_path = self.file_system_plugin.find_contract_by_vendor(vendor_name)
            
            if contract_path and os.path.exists(contract_path):
                # Contract found in file system but not in database, add to database
                contract_data = {
                    "vendor_name": vendor_name,
                    "file_path": contract_path
                }
                
                # This would be better with a proper create_contract method
                # For now, we'll just return the contract path
                return {
                    "contract_path": contract_path,
                    "vendor_name": vendor_name,
                    "source": "file_system"
                }
            
            # Step 3: Contract not found
            return {
                "error": f"No contract found for vendor: {vendor_name}",
                "vendor_name": vendor_name
            }
            
        except Exception as e:
            return {"error": f"Error retrieving contract: {str(e)}"}