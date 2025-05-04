from typing import Dict, Any, Optional
import json
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelPlugin
from semantic_kernel.functions import KernelFunction

class NLPPlugin(KernelPlugin):
    """
    Plugin for natural language processing and structuring using LLMs.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialize the NLP plugin.
        
        Args:
            kernel: Semantic Kernel instance.
        """
        self.kernel = kernel
    
    @kernel_function(
        description="Extract structured data from OCR text",
        name="extract_invoice_data"
    )
    async def extract_invoice_data(self, ocr_text: str) -> str:
        """
        Extract structured invoice data from OCR text.
        
        Args:
            ocr_text: OCR text from an invoice.
            
        Returns:
            JSON string containing the extracted invoice data.
        """
        prompt = f"""
        You are an AI assistant that extracts structured data from invoice OCR text.
        
        Extract the following information from the invoice text:
        - Vendor Name
        - Invoice Number
        - Invoice Date (in ISO format YYYY-MM-DD if possible)
        - Total Amount (numeric value only)
        - Line Items (as an array of objects with description, quantity, unit price, and total)
        
        Here is the OCR text from the invoice:
        
        {ocr_text}
        
        Return the extracted data as a valid JSON object with the following structure:
        {{
            "vendor_name": "string",
            "invoice_number": "string",
            "invoice_date": "string",
            "total_amount": number,
            "line_items": [
                {{
                    "description": "string",
                    "quantity": number,
                    "unit_price": number,
                    "total": number
                }}
            ]
        }}
        
        If you cannot extract some fields, use null for those fields. Make sure the JSON is valid.
        """
        
        # Create a function to run the prompt
        function = self.kernel.create_function_from_prompt(prompt)
        
        # Execute the function
        result = await self.kernel.invoke(function)
        
        # Ensure the result is valid JSON
        try:
            json_result = json.loads(str(result))
            return json.dumps(json_result, indent=2)
        except json.JSONDecodeError:
            # If the result is not valid JSON, try to fix it or return an error
            return json.dumps({
                "error": "Failed to parse extracted data as JSON",
                "raw_result": str(result)
            }, indent=2)
    
    @kernel_function(
        description="Extract key terms from contract text",
        name="extract_contract_terms"
    )
    async def extract_contract_terms(self, contract_text: str) -> str:
        """
        Extract key terms from contract text.
        
        Args:
            contract_text: Text from a contract.
            
        Returns:
            JSON string containing the extracted contract terms.
        """
        prompt = f"""
        You are an AI assistant that extracts key terms from contract text.
        
        Extract the following information from the contract text:
        - Start Date (in ISO format YYYY-MM-DD if possible)
        - End Date (in ISO format YYYY-MM-DD if possible)
        - Payment Terms (e.g., Net 30, Net 60)
        - Pricing Information (as an array of items with description and price)
        - Delivery Terms
        - Termination Conditions
        - Other Important Clauses
        
        Here is the text from the contract:
        
        {contract_text}
        
        Return the extracted data as a valid JSON object with the following structure:
        {{
            "start_date": "string",
            "end_date": "string",
            "payment_terms": "string",
            "pricing": [
                {{
                    "description": "string",
                    "price": number
                }}
            ],
            "delivery_terms": "string",
            "termination_conditions": "string",
            "important_clauses": [
                {{
                    "title": "string",
                    "description": "string"
                }}
            ]
        }}
        
        If you cannot extract some fields, use null for those fields. Make sure the JSON is valid.
        """
        
        # Create a function to run the prompt
        function = self.kernel.create_function_from_prompt(prompt)
        
        # Execute the function
        result = await self.kernel.invoke(function)
        
        # Ensure the result is valid JSON
        try:
            json_result = json.loads(str(result))
            return json.dumps(json_result, indent=2)
        except json.JSONDecodeError:
            # If the result is not valid JSON, try to fix it or return an error
            return json.dumps({
                "error": "Failed to parse extracted data as JSON",
                "raw_result": str(result)
            }, indent=2)
    
    @kernel_function(
        description="Compare invoice data against contract terms",
        name="validate_invoice_against_contract"
    )
    async def validate_invoice_against_contract(self, invoice_data: str, contract_terms: str) -> str:
        """
        Compare invoice data against contract terms to identify discrepancies.
        
        Args:
            invoice_data: JSON string containing invoice data.
            contract_terms: JSON string containing contract terms.
            
        Returns:
            JSON string containing validation results.
        """
        prompt = f"""
        You are an AI assistant that validates invoice data against contract terms.
        
        Compare the invoice data with the contract terms and identify any discrepancies or issues.
        Focus on:
        - Price mismatches
        - Item mismatches
        - Date issues (e.g., invoice date outside contract period)
        - Payment term violations
        - Any other policy violations
        
        Invoice Data:
        {invoice_data}
        
        Contract Terms:
        {contract_terms}
        
        Return the validation results as a valid JSON object with the following structure:
        {{
            "is_valid": boolean,
            "discrepancies": [
                {{
                    "type": "string", // e.g., "price_mismatch", "item_mismatch", "date_issue", "payment_term", "other"
                    "description": "string",
                    "severity": "string" // "high", "medium", "low"
                }}
            ],
            "summary": "string"
        }}
        
        If there are no discrepancies, set is_valid to true and provide an empty array for discrepancies.
        Make sure the JSON is valid.
        """
        
        # Create a function to run the prompt
        function = self.kernel.create_function_from_prompt(prompt)
        
        # Execute the function
        result = await self.kernel.invoke(function)
        
        # Ensure the result is valid JSON
        try:
            json_result = json.loads(str(result))
            return json.dumps(json_result, indent=2)
        except json.JSONDecodeError:
            # If the result is not valid JSON, try to fix it or return an error
            return json.dumps({
                "error": "Failed to parse validation results as JSON",
                "raw_result": str(result)
            }, indent=2)
    
    @kernel_function(
        description="Summarize text",
        name="summarize_text"
    )
    async def summarize_text(self, text: str, max_length: Optional[int] = 500) -> str:
        """
        Summarize text.
        
        Args:
            text: Text to summarize.
            max_length: Maximum length of the summary in characters.
            
        Returns:
            Summarized text.
        """
        prompt = f"""
        You are an AI assistant that summarizes text.
        
        Summarize the following text in a clear and concise manner.
        The summary should be no longer than {max_length} characters.
        
        Text to summarize:
        {text}
        
        Summary:
        """
        
        # Create a function to run the prompt
        function = self.kernel.create_function_from_prompt(prompt)
        
        # Execute the function
        result = await self.kernel.invoke(function)
        
        return str(result)