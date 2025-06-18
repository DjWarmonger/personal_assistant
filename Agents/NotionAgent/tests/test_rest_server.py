import pytest
from http import HTTPStatus
from unittest.mock import patch

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

from Agents.NotionAgent.launcher.rest_server import app

# API endpoint constants
API_PROCESS_ENDPOINT = "/api/v1/process"

@pytest.fixture
def client():
	app.testing = True
	return app.test_client()

@patch('Agents.NotionAgent.launcher.rest_server.chat')
def test_process_ok_mocked(mock_chat, client):
	"""Test REST server with mocked chat function - fast unit test"""
	mock_chat.return_value = "Mocked response for testing"
	
	r = client.post(API_PROCESS_ENDPOINT, json={"input": "Hello"})
	assert r.status_code == HTTPStatus.OK
	response_data = r.get_json()
	assert "result" in response_data
	assert response_data["result"] == "Mocked response for testing"
	
	# Verify mock was called with correct parameters
	mock_chat.assert_called_once_with(loop=False, user_prompt="Hello")


@patch('Agents.NotionAgent.launcher.rest_server.chat')
def test_process_ok_mocked_exception(mock_chat, client):
	"""Test REST server error handling with mocked chat function"""
	mock_chat.side_effect = ValueError("Test error")
	
	r = client.post(API_PROCESS_ENDPOINT, json={"input": "Hello"})
	assert r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
	response_data = r.get_json()
	assert "error" in response_data
	assert "Test error" in response_data["error"]


@patch('Agents.NotionAgent.launcher.rest_server.chat')
def test_process_ok_mocked_empty_response(mock_chat, client):
	"""Test REST server with empty response from mocked chat function"""
	mock_chat.return_value = ""
	
	r = client.post(API_PROCESS_ENDPOINT, json={"input": "Hello"})
	assert r.status_code == HTTPStatus.OK
	response_data = r.get_json()
	assert "result" in response_data
	assert response_data["result"] == ""


# def test_process_ok_integration(client):
# 	"""Integration test - calls real chat function (slow)"""
# 	r = client.post(API_PROCESS_ENDPOINT, json={"input": "Hello"})
# 	# Accept either success or error response (since chat function may have issues)
# 	response_data = r.get_json()
# 	assert r.status_code in [HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR]
# 	assert "result" in response_data or "error" in response_data

def test_process_missing_input(client):
	r = client.post(API_PROCESS_ENDPOINT, json={})
	assert r.status_code == HTTPStatus.BAD_REQUEST
	assert r.get_json()["error"] == "input required"

def test_health(client):
	r = client.get("/health")
	assert r.status_code == HTTPStatus.OK
	assert r.get_json()["status"] == "ok" 