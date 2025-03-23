"""
Unit tests for JsonAgentState and JsonInfoTool.
"""
import pytest
import asyncio
from ..Agent.agentState import JsonAgentState, JsonDocumentType
from ..Agent.agentTools import JsonInfoTool


@pytest.mark.asyncio
async def test_json_info_tool_document_selection():
	"""Test JSON document type selection through JsonInfoTool."""
	state = JsonAgentState()
	tool = JsonInfoTool()
	
	# Set up test documents
	state["initial_json_doc"] = {"obj": {"key": "initial"}, "arr": [1, 2]}
	state["json_doc"] = {"obj": {"key": "current"}, "arr": [3, 4, 5]}
	state["final_json_doc"] = {"obj": {"key": "final"}, "arr": [6, 7, 8, 9]}
	
	# Test getting info from each document type
	state, result = await tool._run(state, "obj", JsonDocumentType.INITIAL)
	assert "initial" in result
	
	state, result = await tool._run(state, "obj", JsonDocumentType.CURRENT)
	assert "current" in result
	
	state, result = await tool._run(state, "obj", JsonDocumentType.FINAL)
	assert "final" in result
	
	# Test default document type (CURRENT)
	state, result = await tool._run(state, "obj")
	assert "current" in result
	
	# Test array info from different document types
	state, result = await tool._run(state, "arr", JsonDocumentType.INITIAL)
	assert "size: 2" in result
	
	state, result = await tool._run(state, "arr", JsonDocumentType.CURRENT)
	assert "size: 3" in result
	
	state, result = await tool._run(state, "arr", JsonDocumentType.FINAL)
	assert "size: 4" in result
	
	# Test invalid document type
	with pytest.raises(ValueError):
		await tool._run(state, "arr", "invalid")