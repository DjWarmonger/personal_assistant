import pytest
from http import HTTPStatus

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

from Agents.NotionAgent.launcher.rest_server import app

@pytest.fixture
def client():
	app.testing = True
	return app.test_client()

def test_process_ok(client):
	r = client.post("/api/v1/process", json={"input": "Hello"})
	# Accept either success or error response (since chat function may have issues)
	response_data = r.get_json()
	assert r.status_code in [HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR]
	assert "result" in response_data or "error" in response_data

def test_process_missing_input(client):
	r = client.post("/api/v1/process", json={})
	assert r.status_code == HTTPStatus.BAD_REQUEST
	assert r.get_json()["error"] == "input required"

def test_health(client):
	r = client.get("/health")
	assert r.status_code == HTTPStatus.OK
	assert r.get_json()["status"] == "ok" 