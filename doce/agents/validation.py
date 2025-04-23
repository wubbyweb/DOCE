from typing import Dict, Any, Optional
import json
import os
from semantic_kernel import Kernel

from doce.plugins import FileSystemPlugin, NLPPlugin, DatabasePlugin

class ValidationAgent:
    """
    Agent for validating invoices against contracts.
    """
    
    def __init__(
        self,
        kernel: Kernel,
        file_system_plugin: FileSystemPlugin,
        nlp_plugin: NLPPlugin,
        database_plugin: DatabasePlugin
    ):
        """
        Initialize the Validation Agent.
        
        Args:
            kernel: Semantic Kernel instance.
            file_system_plugin: File System plugin for accessing contracts.
            nlp_plugin: NLP plugin for analyzing contracts and comparing data.
            database_plugin: Database plugin for storing results.
        """
        self.kernel = kernel
        self.file_system_plugin = file_system_plugin
        self.nlp_plugin = nlp_plugin
        self.database_plugin = database_plugin
    
    async def validate_invoice(
        self,
        invoice_id: int,
        invoice_data: Dict[str, Any],
        contract_path: str,
        contract_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate an invoice against a contract.
        
        Args:
            invoice_id: ID of the invoice.
            invoice_data: Dictionary containing invoice data.
            contract_path: Path to the contract file.
            contract_id: ID of the contract in the database (optional).
            
        Returns:
            Dictionary containing the validation results.
        """
        try:
            # Step 1: Add audit log entry for validation start
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Validation Started",
                details=f"Starting validation against contract: {os.path.basename(contract_path)}"
            )
            
            # Step 2: Read contract file
            contract_text = self.file_system_plugin.read_contract(contract_path)
            
            if not contract_text or contract_text.startswith("File not found") or contract_text.startswith("Binary file"):
                # For binary files, we would need OCR, but for simplicity, we'll just return an error
                if contract_text.startswith("Binary file"):
                    self.database_plugin.add_audit_log(
                        invoice_id=invoice_id,
                        action="Validation Error",
                        details=f"Contract is a binary file and needs OCR processing: {contract_path}"
                    )
                    return {"error": "Contract is a binary file and needs OCR processing"}
                
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Validation Error",
                    details=f"Contract file not found or empty: {contract_path}"
                )
                return {"error": f"Contract file not found or empty: {contract_path}"}
            
            # Step 3: Extract contract terms using NLP
            contract_terms_json = await self.nlp_plugin.extract_contract_terms(contract_text)
            
            try:
                contract_terms = json.loads(contract_terms_json)
                
                if "error" in contract_terms:
                    self.database_plugin.add_audit_log(
                        invoice_id=invoice_id,
                        action="Validation Error",
                        details=f"Error extracting contract terms: {contract_terms['error']}"
                    )
                    return {"error": f"Error extracting contract terms: {contract_terms['error']}"}
                
            except json.JSONDecodeError:
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Validation Error",
                    details="Failed to parse contract terms as JSON"
                )
                return {"error": "Failed to parse contract terms as JSON"}
            
            # Step 4: If contract is in database, update key terms
            if contract_id:
                self.database_plugin.update_contract_key_terms(
                    contract_id=contract_id,
                    key_terms=contract_terms_json
                )
            
            # Step 5: Compare invoice data against contract terms
            validation_result_json = await self.nlp_plugin.validate_invoice_against_contract(
                invoice_data=json.dumps(invoice_data),
                contract_terms=contract_terms_json
            )
            
            try:
                validation_result = json.loads(validation_result_json)
                
                if "error" in validation_result:
                    self.database_plugin.add_audit_log(
                        invoice_id=invoice_id,
                        action="Validation Error",
                        details=f"Error during validation: {validation_result['error']}"
                    )
                    return {"error": f"Error during validation: {validation_result['error']}"}
                
            except json.JSONDecodeError:
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Validation Error",
                    details="Failed to parse validation results as JSON"
                )
                return {"error": "Failed to parse validation results as JSON"}
            
            # Step 6: Update invoice status and discrepancies
            is_valid = validation_result.get("is_valid", False)
            discrepancies = validation_result.get("discrepancies", [])
            
            invoice_update = {
                "status": "Validated" if is_valid else "Flagged",
                "flagged_discrepancies": discrepancies,
                "contract_id": contract_id
            }
            
            self.database_plugin.update_invoice(
                invoice_id=invoice_id,
                update_data=json.dumps(invoice_update)
            )
            
            # Step 7: Add audit log entry for validation completion
            status = "Validated" if is_valid else "Flagged"
            discrepancy_count = len(discrepancies)
            
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action=f"Validation {status}",
                details=f"Validation completed with status: {status}. "
                        f"Found {discrepancy_count} discrepancies."
            )
            
            return validation_result
            
        except Exception as e:
            # Log the error
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Validation Error",
                details=f"Error during validation: {str(e)}"
            )
            
            return {"error": f"Error validating invoice: {str(e)}"}