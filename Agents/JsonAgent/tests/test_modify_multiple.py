"""
Unit tests for JsonModifyMultipleTool.
"""
import pytest
from copy import deepcopy

from ..Agent.agentTools import JsonModifyMultipleTool, JsonDocumentType
from ..Agent.agentState import JsonAgentState


@pytest.fixture
def test_data():
	"""Test data fixture."""
	return {
		"products": [
			{"id": 1, "name": "laptop", "price": 1000.00, "in_stock": True, "categories": [], "metadata": {}},
			{"id": 2, "name": "monitor", "price": 400.00, "in_stock": True, "categories": [], "metadata": {}},
			{"id": 3, "name": "keyboard", "price": 80.00, "in_stock": False, "categories": [], "metadata": {}}
		],
		"settings": {
			"features": {
				"dark_mode": {"enabled": True, "version": "1.0"},
				"auto_save": {"enabled": True, "version": "2.0"},
				"notifications": {"enabled": False, "version": "1.5"}
			}
		},
		"zones": [
			{"id": "z1", "zoneLimit": "5"},
			{"id": "z2", "zoneLimit": "10"},
			{"id": "z3", "zoneLimit": "15"}
		]
	}


@pytest.fixture
def tool_and_state(test_data):
	"""Tool and state fixture."""
	tool = JsonModifyMultipleTool()
	state = JsonAgentState()
	state["json_doc"] = deepcopy(test_data)
	return tool, state


@pytest.mark.asyncio
async def test_direct_value_replacement(tool_and_state):
	"""Test direct value replacement for feature flags."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "settings.features.*.enabled", True)
	
	assert result_state["json_doc"]["settings"]["features"]["dark_mode"]["enabled"] == True
	assert result_state["json_doc"]["settings"]["features"]["auto_save"]["enabled"] == True
	assert result_state["json_doc"]["settings"]["features"]["notifications"]["enabled"] == True
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_direct_string_replacement(tool_and_state):
	"""Test direct string value replacement."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "zones.*.zoneLimit", "1")
	
	assert result_state["json_doc"]["zones"][0]["zoneLimit"] == "1"
	assert result_state["json_doc"]["zones"][1]["zoneLimit"] == "1"
	assert result_state["json_doc"]["zones"][2]["zoneLimit"] == "1"
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_json_list_replacement(tool_and_state):
	"""Test JSON list value replacement."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.categories", '["electronics", "computers"]')
	
	assert result_state["json_doc"]["products"][0]["categories"] == ["electronics", "computers"]
	assert result_state["json_doc"]["products"][1]["categories"] == ["electronics", "computers"]
	assert result_state["json_doc"]["products"][2]["categories"] == ["electronics", "computers"]
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_json_object_replacement(tool_and_state):
	"""Test JSON object value replacement."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.metadata", '{"source": "import", "batch": 123}')
	
	assert result_state["json_doc"]["products"][0]["metadata"] == {"source": "import", "batch": 123}
	assert result_state["json_doc"]["products"][1]["metadata"] == {"source": "import", "batch": 123}
	assert result_state["json_doc"]["products"][2]["metadata"] == {"source": "import", "batch": 123}
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_number_transformation(tool_and_state):
	"""Test numeric transformation using lambda function for price discount."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.price", "lambda x: round(x * 0.8, 2)")
	
	assert result_state["json_doc"]["products"][0]["price"] == 800.00
	assert result_state["json_doc"]["products"][1]["price"] == 320.00
	assert result_state["json_doc"]["products"][2]["price"] == 64.00
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_string_transformation(tool_and_state):
	"""Test string transformation using lambda function for product names."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.name", "lambda x: x.title()")
	
	assert result_state["json_doc"]["products"][0]["name"] == "Laptop"
	assert result_state["json_doc"]["products"][1]["name"] == "Monitor"
	assert result_state["json_doc"]["products"][2]["name"] == "Keyboard"
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_id_formatting(tool_and_state):
	"""Test ID formatting using string operations."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.id", "lambda x: str(x).zfill(3)")
	
	assert result_state["json_doc"]["products"][0]["id"] == "001"
	assert result_state["json_doc"]["products"][1]["id"] == "002"
	assert result_state["json_doc"]["products"][2]["id"] == "003"
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_constant_lambda(tool_and_state):
	"""Test lambda that returns a constant value."""
	tool, state = tool_and_state
	
	result_state, message = await tool._run(state, "products.*.in_stock", "lambda x: True")
	
	assert result_state["json_doc"]["products"][0]["in_stock"] == True
	assert result_state["json_doc"]["products"][1]["in_stock"] == True
	assert result_state["json_doc"]["products"][2]["in_stock"] == True
	assert "Modified 3 JSON document" in message


@pytest.mark.asyncio
async def test_invalid_lambda_expression(tool_and_state):
	"""Test handling of invalid lambda expressions."""
	tool, state = tool_and_state
	
	with pytest.raises(ValueError, match="Failed to apply replacement to value '1000.0': name 'invalid_function' is not defined"):
		await tool._run(state, "products.*.price", "lambda x: invalid_function(x)")


@pytest.mark.asyncio
async def test_lambda_syntax_error(tool_and_state):
	"""Test handling of lambda syntax errors."""
	tool, state = tool_and_state
	
	with pytest.raises(ValueError, match="Invalid lambda expression: invalid syntax"):
		await tool._run(state, "products.*.price", "lambda x: :")


@pytest.mark.asyncio
async def test_lambda_runtime_error(tool_and_state):
	"""Test handling of lambda runtime errors."""
	tool, state = tool_and_state
	
	with pytest.raises(ValueError, match="Failed to apply replacement to value '1000.0': 'float' object has no attribute 'title'"):
		await tool._run(state, "products.*.price", "lambda x: x.title()")


@pytest.mark.asyncio
async def test_invalid_json_string(tool_and_state):
	"""Test handling of invalid JSON string."""
	tool, state = tool_and_state
	
	# Invalid JSON should be treated as plain string
	result_state, message = await tool._run(state, "products.*.name", "{not valid json}")
	
	assert result_state["json_doc"]["products"][0]["name"] == "{not valid json}"
	assert result_state["json_doc"]["products"][1]["name"] == "{not valid json}"
	assert result_state["json_doc"]["products"][2]["name"] == "{not valid json}"
	assert "Modified 3 JSON document" in message 