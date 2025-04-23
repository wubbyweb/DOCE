from typing import Dict, Any
import json
from semantic_kernel import Kernel

from doce.plugins import WorkflowRulesPlugin, DatabasePlugin

class WorkflowAgent:
    """
    Agent for managing workflow decisions based on validation results.
    """
    
    def __init__(
        self,
        kernel: Kernel,
        workflow_rules_plugin: WorkflowRulesPlugin,
        database_plugin: DatabasePlugin
    ):
        """
        Initialize the Workflow Agent.
        
        Args:
            kernel: Semantic Kernel instance.
            workflow_rules_plugin: Workflow Rules plugin for decision making.
            database_plugin: Database plugin for storing results.
        """
        self.kernel = kernel
        self.workflow_rules_plugin = workflow_rules_plugin
        self.database_plugin = database_plugin
        
        # Load workflow rules from database
        self._load_workflow_rules()
    
    def _load_workflow_rules(self):
        """
        Load workflow rules from the database.
        """
        try:
            rules_json = self.database_plugin.get_workflow_rules()
            rules = json.loads(rules_json)
            
            # Set rules in the plugin
            self.workflow_rules_plugin.set_rules(rules)
            
        except Exception as e:
            # If there's an error, we'll just use default rules
            default_rules = [
                {
                    "name": "Auto-Approve Validated Small Invoices",
                    "condition": "IsValidated AND Amount < 1000",
                    "action": "AutoApprove",
                    "priority": 100,
                    "is_active": True
                },
                {
                    "name": "Manager Review for Flagged Invoices",
                    "condition": "IsFlagged",
                    "action": "RequireManagerApproval",
                    "priority": 90,
                    "is_active": True
                },
                {
                    "name": "Manager Review for Large Invoices",
                    "condition": "Amount >= 1000",
                    "action": "RequireManagerApproval",
                    "priority": 80,
                    "is_active": True
                },
                {
                    "name": "Default Rule",
                    "condition": "true",
                    "action": "RequireReview",
                    "priority": 0,
                    "is_active": True
                }
            ]
            
            self.workflow_rules_plugin.set_rules(default_rules)
    
    async def process_validation_result(self, invoice_id: int, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process validation results and determine next steps.
        
        Args:
            invoice_id: ID of the invoice.
            validation_result: Dictionary containing validation results.
            
        Returns:
            Dictionary containing the workflow decision.
        """
        try:
            # Step 1: Add audit log entry for workflow processing
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Workflow Processing",
                details="Determining next steps based on validation results"
            )
            
            # Step 2: Get invoice data
            invoice_json = self.database_plugin.get_invoice(invoice_id)
            
            try:
                invoice_data = json.loads(invoice_json)
                
                if "error" in invoice_data:
                    self.database_plugin.add_audit_log(
                        invoice_id=invoice_id,
                        action="Workflow Error",
                        details=f"Error retrieving invoice data: {invoice_data['error']}"
                    )
                    return {"error": f"Error retrieving invoice data: {invoice_data['error']}"}
                
            except json.JSONDecodeError:
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Workflow Error",
                    details="Failed to parse invoice data as JSON"
                )
                return {"error": "Failed to parse invoice data as JSON"}
            
            # Step 3: Get next action based on validation result
            next_action_json = self.workflow_rules_plugin.get_next_action(json.dumps(validation_result))
            
            try:
                next_action = json.loads(next_action_json)
                
                if "error" in next_action:
                    self.database_plugin.add_audit_log(
                        invoice_id=invoice_id,
                        action="Workflow Error",
                        details=f"Error determining next action: {next_action['error']}"
                    )
                    return {"error": f"Error determining next action: {next_action['error']}"}
                
            except json.JSONDecodeError:
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Workflow Error",
                    details="Failed to parse next action as JSON"
                )
                return {"error": "Failed to parse next action as JSON"}
            
            # Step 4: Process the action
            action = next_action.get("action", "RequireReview")
            reason = next_action.get("reason", "Default workflow decision")
            
            # Handle different actions
            if action == "AutoApprove":
                # Auto-approve the invoice
                invoice_update = {
                    "status": "Approved"
                    # In a real system, we would set approved_by_id to a system user
                    # and set approval_timestamp
                }
                
                self.database_plugin.update_invoice(
                    invoice_id=invoice_id,
                    update_data=json.dumps(invoice_update)
                )
                
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Auto-Approved",
                    details=f"Invoice auto-approved. Reason: {reason}"
                )
                
            elif action == "RequireManagerApproval":
                # Update status to require manager approval
                invoice_update = {
                    "status": "Pending Approval"
                }
                
                self.database_plugin.update_invoice(
                    invoice_id=invoice_id,
                    update_data=json.dumps(invoice_update)
                )
                
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Requires Manager Approval",
                    details=f"Invoice requires manager approval. Reason: {reason}"
                )
                
            else:  # RequireReview or any other action
                # Update status to require review
                invoice_update = {
                    "status": "Pending Review"
                }
                
                self.database_plugin.update_invoice(
                    invoice_id=invoice_id,
                    update_data=json.dumps(invoice_update)
                )
                
                self.database_plugin.add_audit_log(
                    invoice_id=invoice_id,
                    action="Requires Review",
                    details=f"Invoice requires review. Reason: {reason}"
                )
            
            # Step 5: Return the workflow decision
            return {
                "invoice_id": invoice_id,
                "action": action,
                "reason": reason,
                "is_valid": validation_result.get("is_valid", False),
                "discrepancies": validation_result.get("discrepancies", [])
            }
            
        except Exception as e:
            # Log the error
            self.database_plugin.add_audit_log(
                invoice_id=invoice_id,
                action="Workflow Error",
                details=f"Error during workflow processing: {str(e)}"
            )
            
            return {"error": f"Error processing workflow: {str(e)}"}