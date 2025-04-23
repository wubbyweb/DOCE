from typing import Dict, Any
import json
import os
from semantic_kernel import Kernel

from doce.plugins import GoogleVisionPlugin, NLPPlugin, DatabasePlugin

class InvoiceProcessingAgent:
    """
    Agent for processing invoices using OCR and NLP.
    """
    
    def __init__(
        self,
        kernel: Kernel,
        google_vision_plugin: GoogleVisionPlugin,
        nlp_plugin: NLPPlugin,
        database_plugin: DatabasePlugin
    ):
        """
        Initialize the Invoice Processing Agent.
        
        Args:
            kernel: Semantic Kernel instance.
            google_vision_plugin: Google Vision OCR plugin.
            nlp_plugin: NLP plugin for structuring data.
            database_plugin: Database plugin for storing results.
        """
        self.kernel = kernel
        self.google_vision_plugin = google_vision_plugin
        self.nlp_plugin = nlp_plugin
        self.database_plugin = database_plugin
    
    async def process_invoice(self, invoice_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process an invoice file.
        
        Args:
            invoice_id: ID of the invoice.
            file_path: Path to the invoice file.
            
        Returns:
            Dictionary containing the extracted invoice data.
        """
        try:
            # Step 1: Add audit log entry for OCR start
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="OCR Started",
                details=f"Starting OCR processing for file: {os.path.basename(file_path)}"
            )
            
            # Step 2: Perform OCR using Google Vision
            ocr_text = self.google_vision_plugin.extract_text(file_path)
            
            if not ocr_text:
                return {"error": "No text extracted from invoice"}
            
            # Step 3: Add audit log entry for OCR completion
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="OCR Completed",
                details=f"OCR processing completed with {len(ocr_text)} characters extracted"
            )
            
            # Step 4: Extract structured data using NLP
            extracted_data_json = await self.nlp_plugin.extract_invoice_data(ocr_text)
            
            try:
                extracted_data = json.loads(extracted_data_json)
                
                if "error" in extracted_data:
                    return {"error": f"Error extracting data: {extracted_data['error']}"}
                
            except json.JSONDecodeError:
                return {"error": "Failed to parse extracted data as JSON"}
            
            # Step 5: Update invoice record with extracted data
            invoice_update = {
                "vendor_name": extracted_data.get("vendor_name"),
                "invoice_number": extracted_data.get("invoice_number"),
                "invoice_date": extracted_data.get("invoice_date"),
                "total_amount": extracted_data.get("total_amount"),
                "extracted_data": extracted_data,
                "status": "OCRd"
            }
            
            update_result = self.database_plugin.update_invoice(
                invoice_id=invoice_id,
                update_data=json.dumps(invoice_update)
            )
            
            # Step 6: Add audit log entry for data extraction
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Data Extraction Completed",
                details=f"Extracted vendor: {extracted_data.get('vendor_name')}, "
                        f"invoice #: {extracted_data.get('invoice_number')}, "
                        f"amount: {extracted_data.get('total_amount')}"
            )
            
            return extracted_data
            
        except Exception as e:
            # Log the error
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Processing Error",
                details=f"Error during invoice processing: {str(e)}"
            )
            
            return {"error": f"Error processing invoice: {str(e)}"}