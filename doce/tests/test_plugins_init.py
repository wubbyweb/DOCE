import pytest
from unittest.mock import MagicMock

from doce.plugins import (
    GoogleVisionPlugin,
    FileSystemPlugin,
    DatabasePlugin,
    NLPPlugin,
    WorkflowRulesPlugin
)


def test_google_vision_plugin_import():
    # Verify that GoogleVisionPlugin is properly imported
    assert GoogleVisionPlugin is not None
    
    # Create an instance to verify the class structure
    plugin = GoogleVisionPlugin()
    
    # Verify that the plugin has the expected methods
    assert hasattr(plugin, 'extract_text')
    assert callable(plugin.extract_text)


def test_file_system_plugin_import():
    # Verify that FileSystemPlugin is properly imported
    assert FileSystemPlugin is not None
    
    # Create an instance to verify the class structure
    plugin = FileSystemPlugin(contract_path="/test/contracts")
    
    # Verify that the plugin has the expected attributes
    assert hasattr(plugin, 'contract_path')
    
    # Verify that the plugin has the expected methods
    assert hasattr(plugin, 'find_contract_by_vendor')
    assert callable(plugin.find_contract_by_vendor)
    assert hasattr(plugin, 'read_contract')
    assert callable(plugin.read_contract)
    assert hasattr(plugin, 'list_contracts')
    assert callable(plugin.list_contracts)


def test_database_plugin_import():
    # Verify that DatabasePlugin is properly imported
    assert DatabasePlugin is not None
    
    # Create an instance to verify the class structure
    db = MagicMock()
    plugin = DatabasePlugin(db=db)
    
    # Verify that the plugin has the expected attributes
    assert hasattr(plugin, 'db')
    
    # Verify that the plugin has the expected methods
    assert hasattr(plugin, 'get_invoice')
    assert callable(plugin.get_invoice)
    assert hasattr(plugin, 'update_invoice')
    assert callable(plugin.update_invoice)
    assert hasattr(plugin, 'get_contract_by_vendor')
    assert callable(plugin.get_contract_by_vendor)
    assert hasattr(plugin, 'update_contract_key_terms')
    assert callable(plugin.update_contract_key_terms)
    assert hasattr(plugin, 'add_audit_log')
    assert callable(plugin.add_audit_log)
    assert hasattr(plugin, 'get_workflow_rules')
    assert callable(plugin.get_workflow_rules)
    assert hasattr(plugin, 'get_user')
    assert callable(plugin.get_user)
    assert hasattr(plugin, 'get_user_by_email')
    assert callable(plugin.get_user_by_email)


def test_nlp_plugin_import():
    # Verify that NLPPlugin is properly imported
    assert NLPPlugin is not None
    
    # Create an instance to verify the class structure
    kernel = MagicMock()
    plugin = NLPPlugin(kernel=kernel)
    
    # Verify that the plugin has the expected attributes
    assert hasattr(plugin, 'kernel')
    
    # Verify that the plugin has the expected methods
    assert hasattr(plugin, 'extract_invoice_data')
    assert callable(plugin.extract_invoice_data)
    assert hasattr(plugin, 'extract_contract_terms')
    assert callable(plugin.extract_contract_terms)
    assert hasattr(plugin, 'validate_invoice_against_contract')
    assert callable(plugin.validate_invoice_against_contract)
    assert hasattr(plugin, 'summarize_text')
    assert callable(plugin.summarize_text)


def test_workflow_rules_plugin_import():
    # Verify that WorkflowRulesPlugin is properly imported
    assert WorkflowRulesPlugin is not None
    
    # Create an instance to verify the class structure
    plugin = WorkflowRulesPlugin()
    
    # Verify that the plugin has the expected attributes
    assert hasattr(plugin, 'rules')
    
    # Verify that the plugin has the expected methods
    assert hasattr(plugin, 'set_rules')
    assert callable(plugin.set_rules)
    assert hasattr(plugin, 'get_next_action')
    assert callable(plugin.get_next_action)
    assert hasattr(plugin, 'evaluate_rules')
    assert callable(plugin.evaluate_rules)
    assert hasattr(plugin, 'create_rule')
    assert callable(plugin.create_rule)