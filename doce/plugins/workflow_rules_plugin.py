from typing import Dict, Any, List
import json
import re
from semantic_kernel.plugin_definition import kernel_function, KernelPlugin

class WorkflowRulesPlugin(KernelPlugin):
    """
    Plugin for evaluating workflow rules and determining next steps.
    """
    
    def __init__(self, rules: List[Dict[str, Any]] = None):
        """
        Initialize the Workflow Rules plugin.
        
        Args:
            rules: List of workflow rules. If None, rules will be loaded from the database.
        """
        self.rules = rules or []
    
    def set_rules(self, rules: List[Dict[str, Any]]):
        """
        Set the workflow rules.
        
        Args:
            rules: List of workflow rules.
        """
        self.rules = rules
    
    @kernel_function(
        description="Evaluate workflow rules for an invoice",
        name="evaluate_rules"
    )
    def evaluate_rules(self, invoice_data: str) -> str:
        """
        Evaluate workflow rules for an invoice.
        
        Args:
            invoice_data: JSON string containing invoice data.
            
        Returns:
            JSON string containing the evaluation results.
        """
        try:
            # Parse invoice data
            invoice = json.loads(invoice_data)
            
            # If no rules are defined, return default action
            if not self.rules:
                return json.dumps({
                    "action": "RequireReview",
                    "reason": "No workflow rules defined"
                }, indent=2)
            
            # Evaluate each rule in priority order
            for rule in self.rules:
                condition = rule.get("condition", "")
                action = rule.get("action", "")
                
                if not condition or not action:
                    continue
                
                if self._evaluate_condition(condition, invoice):
                    return json.dumps({
                        "action": action,
                        "reason": f"Rule '{rule.get('name', 'Unnamed')}' condition met: {condition}"
                    }, indent=2)
            
            # If no rules match, return default action
            return json.dumps({
                "action": "RequireReview",
                "reason": "No matching workflow rules"
            }, indent=2)
            
        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid JSON data for invoice",
                "action": "RequireReview"
            }, indent=2)
    
    def _evaluate_condition(self, condition: str, invoice: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against invoice data.
        
        Args:
            condition: Condition string (e.g., "Amount > 1000", "IsFlagged").
            invoice: Invoice data.
            
        Returns:
            True if the condition is met, False otherwise.
        """
        # Handle simple conditions
        if condition == "IsFlagged":
            return invoice.get("status") == "Flagged"
        
        if condition == "IsValidated":
            return invoice.get("status") == "Validated"
        
        # Handle amount comparison
        amount_match = re.match(r"Amount\s*([><]=?|==|!=)\s*(\d+(\.\d+)?)", condition)
        if amount_match:
            operator = amount_match.group(1)
            value = float(amount_match.group(2))
            invoice_amount = float(invoice.get("total_amount", 0))
            
            if operator == ">":
                return invoice_amount > value
            elif operator == ">=":
                return invoice_amount >= value
            elif operator == "<":
                return invoice_amount < value
            elif operator == "<=":
                return invoice_amount <= value
            elif operator == "==":
                return invoice_amount == value
            elif operator == "!=":
                return invoice_amount != value
        
        # Handle discrepancy count comparison
        discrepancy_match = re.match(r"DiscrepancyCount\s*([><]=?|==|!=)\s*(\d+)", condition)
        if discrepancy_match:
            operator = discrepancy_match.group(1)
            value = int(discrepancy_match.group(2))
            discrepancies = invoice.get("flagged_discrepancies", [])
            count = len(discrepancies) if isinstance(discrepancies, list) else 0
            
            if operator == ">":
                return count > value
            elif operator == ">=":
                return count >= value
            elif operator == "<":
                return count < value
            elif operator == "<=":
                return count <= value
            elif operator == "==":
                return count == value
            elif operator == "!=":
                return count != value
        
        # Handle vendor condition
        vendor_match = re.match(r"Vendor\s*==\s*['\"](.+)['\"]", condition)
        if vendor_match:
            vendor_name = vendor_match.group(1)
            return invoice.get("vendor_name") == vendor_name
        
        # Handle complex conditions with AND/OR
        if " AND " in condition:
            subconditions = condition.split(" AND ")
            return all(self._evaluate_condition(subcond, invoice) for subcond in subconditions)
        
        if " OR " in condition:
            subconditions = condition.split(" OR ")
            return any(self._evaluate_condition(subcond, invoice) for subcond in subconditions)
        
        # Default to False for unrecognized conditions
        return False
    
    @kernel_function(
        description="Get next action based on validation result",
        name="get_next_action"
    )
    def get_next_action(self, validation_result: str) -> str:
        """
        Get the next action based on validation result.
        
        Args:
            validation_result: JSON string containing validation results.
            
        Returns:
            JSON string containing the next action.
        """
        try:
            # Parse validation result
            result = json.loads(validation_result)
            
            # Create invoice-like object for rule evaluation
            invoice = {
                "status": "Validated" if result.get("is_valid", False) else "Flagged",
                "flagged_discrepancies": result.get("discrepancies", [])
            }
            
            # Evaluate rules
            return self.evaluate_rules(json.dumps(invoice))
            
        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid JSON data for validation result",
                "action": "RequireReview"
            }, indent=2)
    
    @kernel_function(
        description="Create a workflow rule",
        name="create_rule"
    )
    def create_rule(self, name: str, condition: str, action: str, priority: int = 0) -> str:
        """
        Create a workflow rule.
        
        Args:
            name: Name of the rule.
            condition: Condition string.
            action: Action to take when the condition is met.
            priority: Priority of the rule (higher numbers have higher priority).
            
        Returns:
            JSON string containing the created rule.
        """
        rule = {
            "name": name,
            "condition": condition,
            "action": action,
            "priority": priority,
            "is_active": True
        }
        
        self.rules.append(rule)
        
        # Sort rules by priority (descending)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
        
        return json.dumps(rule, indent=2)