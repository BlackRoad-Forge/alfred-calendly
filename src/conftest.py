"""Test configuration - mock the Alfred workflow library for Python 3 compatibility."""

import sys
from unittest.mock import MagicMock

# The bundled workflow library requires Python 2 (cPickle, etc.).
# Mock it out so tests can run under Python 3.
mock_workflow = MagicMock()
mock_workflow.Workflow3.return_value.logger = MagicMock()
mock_workflow.web = MagicMock()

sys.modules["workflow"] = mock_workflow
sys.modules["workflow.web"] = mock_workflow.web
sys.modules["workflow.Workflow3"] = mock_workflow.Workflow3
sys.modules["workflow.background"] = MagicMock()
sys.modules["workflow.notify"] = MagicMock()
sys.modules["workflow.update"] = MagicMock()
