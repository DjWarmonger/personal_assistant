import pytest
from http import HTTPStatus
from rest_server import app

@pytest.fixture
def client():
	app.testing = True
	return app.test_client()

def test_process_ok(client):
	r = client.post("/api/v1/process", json={"input": "abc"})
	assert r.status_code == HTTPStatus.OK
	assert r.get_json()["result"] == "cba"

def test_process_missing_input(client):
	r = client.post("/api/v1/process", json={})
	assert r.status_code == HTTPStatus.BAD_REQUEST