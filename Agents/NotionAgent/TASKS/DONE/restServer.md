# REST Server Implementation Plan

## Overview
Create a minimal Flask REST server that wraps the existing `chat()` functionality following the PROJECT_TEMPLATE structure while keeping chat.py independent for marimo dashboard usage.

## Architecture

### File Structure
```
Agents/NotionAgent/launcher/
├── chat.py                    # Existing chat module (keep unchanged)  
├── rest_server.py            # New REST server (follows PROJECT_TEMPLATE)
└── dashboard.py              # Existing marimo dashboard (uses chat.py directly)

Agents/NotionAgent/tests/
├── test_rest_server.py       # Tests following PROJECT_TEMPLATE pattern
```

### Core Principle
- **Follow Template**: Exact structure from `PROJECT_TEMPLATE/launch/server/rest_server.py`
- **Independence**: `chat.py` remains unchanged and fully functional
- **Wrapper Pattern**: REST server imports and calls existing `chat()` function
- **Stateless**: Each API call is independent (no session state)

## Implementation Plan

### 1. Create `rest_server.py` (Following Template)

#### Dependencies
```python
from flask import Flask, request, jsonify
from http import HTTPStatus
from chat import chat  # Import existing chat function
```

#### Template Structure
```python
app = Flask(__name__)

@app.route('/api/v1/process', methods=['POST'])
def process_request():
	data = request.get_json(silent=True) or {}
	input_text = data.get("input")
	if not input_text:
		return jsonify({"error": "input required"}), HTTPStatus.BAD_REQUEST

	# Replace template placeholder with chat() call
	result = chat(loop=False, user_prompt=input_text)

	return jsonify({"result": result}), HTTPStatus.OK

@app.route('/health', methods=['GET'])
def health():
	return jsonify({"status": "ok"}), HTTPStatus.OK

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8000, debug=True)
```

#### Key Changes from Template
- Replace `result = input_text[::-1]` with `result = chat(loop=False, user_prompt=input_text)`
- Add necessary imports and path setup from `chat.py`
- Keep exact same API contract as template

### 2. API Contract (Following Template)

#### Process Endpoint
```
POST /api/v1/process
Request: {"input": "string"}
Response: {"result": "string"}
Error: {"error": "input required"} (400 for missing input)
```

#### Health Endpoint
```
GET /health
Response: {"status": "ok"}
```

### 3. Create `test_rest_server.py` (Following Template)

#### Test Structure
```python
import pytest
from http import HTTPStatus
from rest_server import app

@pytest.fixture
def client():
	app.testing = True
	return app.test_client()

def test_process_ok(client):
	r = client.post("/api/v1/process", json={"input": "Hello"})
	assert r.status_code == HTTPStatus.OK
	assert "result" in r.get_json()

def test_process_missing_input(client):
	r = client.post("/api/v1/process", json={})
	assert r.status_code == HTTPStatus.BAD_REQUEST

def test_health(client):
	r = client.get("/health")
	assert r.status_code == HTTPStatus.OK
	assert r.get_json()["status"] == "ok"
```

### 4. Path Setup Integration

#### Import Path Setup
```python
import sys
from pathlib import Path

# Reuse path setup from chat.py
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

from chat import chat
```

### 5. Preserve Existing Functionality

#### No Changes Required
- `chat.py` - Keep exactly as is
- `dashboard.py` - Continue using `chat()` directly  
- All existing imports and dependencies

#### Integration Pattern
- Template calls: `result = input_text[::-1]`
- Our implementation: `result = chat(loop=False, user_prompt=input_text)`
- Same API contract, different backend

## Testing Strategy

### Manual Testing (Following Template Examples)
```bash
# Health check
curl http://localhost:8000/health

# Process test
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how are you?"}'
```

### Unit Tests
```bash
# Run from project root
conda activate services
python -m pytest Agents/NotionAgent/tests/test_rest_server.py -v
```

### Integration Tests
- Verify marimo dashboard continues working
- Confirm no import conflicts
- Test chat functionality independently

## Implementation Notes

### What to Follow from Template
- Exact endpoint names (`/api/v1/process`, `/health`)
- Exact request/response field names (`input`, `result`)
- Same error handling pattern
- Same Flask app structure
- Same host/port configuration
- Same test structure and patterns

### What to Change from Template
- Replace `input_text[::-1]` with `chat(loop=False, user_prompt=input_text)`
- Add path setup and imports for chat module
- Add error handling for chat processing failures

### Launch Requirements
- Run from project root: `python Agents/NotionAgent/launcher/rest_server.py`
- Same environment as chat.py: `conda activate services`

## Success Criteria

1. **Template Compliance**: ✅ Exact same API as PROJECT_TEMPLATE
2. **Health endpoint**: ✅ Returns `{"status": "ok"}` with HTTPStatus.OK
3. **Process endpoint**: ✅ Accepts `{"input": "text"}`, returns `{"result": "response"}` or `{"error": "message"}`
4. **Error handling**: ✅ Returns HTTPStatus.BAD_REQUEST for missing input, HTTPStatus.INTERNAL_SERVER_ERROR for processing errors
5. **Tests pass**: ✅ All template-based tests pass using HTTPStatus constants
6. **Independence**: ✅ Marimo dashboard continues working unchanged
7. **No breaking changes**: ✅ Existing functionality preserved

## Implementation Status: COMPLETED

- ✅ `rest_server.py` created following PROJECT_TEMPLATE structure
- ✅ `test_rest_server.py` created with comprehensive test coverage
- ✅ All tests pass (3/3)
- ✅ Manual testing confirms proper API functionality
- ✅ Error handling implemented for both missing input and processing failures
- ✅ Server runs successfully on http://127.0.0.1:8000

## File Locations

- **Implementation**: `Agents/NotionAgent/launcher/rest_server.py`
- **Tests**: `Agents/NotionAgent/tests/test_rest_server.py`
- **Template Reference**: `PROJECT_TEMPLATE/launch/server/rest_server.py`
- **Test Reference**: `PROJECT_TEMPLATE/tests/test_rest_server.py`
