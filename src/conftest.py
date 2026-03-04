"""
Test configuration - provides mock workflow module for Python 3 testing.
The bundled Alfred workflow library is Python 2 only, so we mock it for tests.
"""
import sys
from unittest.mock import Mock, MagicMock


class MockPasswordNotFound(Exception):
    pass


class SettingsDict(dict):
    """Dict subclass with a save() method to mimic workflow settings."""
    def save(self):
        pass


# Create mock workflow module hierarchy
mock_workflow_module = MagicMock()
mock_workflow_module.Workflow3 = MagicMock
mock_workflow_module.PasswordNotFound = MockPasswordNotFound
mock_workflow_module.ICON_ACCOUNT = "icon_account.png"
mock_workflow_module.ICON_EJECT = "icon_eject.png"

mock_web = MagicMock()
mock_workflow_module.web = mock_web

mock_background = MagicMock()
mock_notify = MagicMock()

# Inject mocks into sys.modules before any test imports
sys.modules["workflow"] = mock_workflow_module
sys.modules["workflow.web"] = mock_web
sys.modules["workflow.background"] = mock_background
sys.modules["workflow.notify"] = mock_notify
sys.modules["workflow.update"] = MagicMock()
sys.modules["workflow.Workflow3"] = MagicMock
