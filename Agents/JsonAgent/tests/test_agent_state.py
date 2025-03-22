"""
Unit tests for JsonAgentState and JsonInfoTool.
"""
import pytest
from ..Agent.agentState import JsonAgentState, JsonDocumentType
from ..Agent.agentTools import JsonInfoTool


def test_json_info_tool_document_selection():
	"""Test JSON document type selection through JsonInfoTool."""
	state = JsonAgentState()
	tool = JsonInfoTool()
	
	# Set up test documents
	state.initial_json_doc = {"obj": {"key": "initial"}, "arr": [1, 2]}
	state.json_doc = {"obj": {"key": "current"}, "arr": [3, 4, 5]}
	state.final_json_doc = {"obj": {"key": "final"}, "arr": [6, 7, 8, 9]}
	
	# Test getting info from each document type
	_, result = tool._run(state, "obj", JsonDocumentType.INITIAL)
	assert "initial" in result
	
	_, result = tool._run(state, "obj", JsonDocumentType.CURRENT)
	assert "current" in result
	
	_, result = tool._run(state, "obj", JsonDocumentType.FINAL)
	assert "final" in result
	
	# Test default document type (CURRENT)
	_, result = tool._run(state, "obj")
	assert "current" in result
	
	# Test array info from different document types
	_, result = tool._run(state, "arr", JsonDocumentType.INITIAL)
	assert "size: 2" in result
	
	_, result = tool._run(state, "arr", JsonDocumentType.CURRENT)
	assert "size: 3" in result
	
	_, result = tool._run(state, "arr", JsonDocumentType.FINAL)
	assert "size: 4" in result
	
	# Test invalid document type
	with pytest.raises(ValueError):
		tool._get_json_doc(state, "invalid") 