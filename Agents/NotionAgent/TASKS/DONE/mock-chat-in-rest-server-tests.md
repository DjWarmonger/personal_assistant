# Mock Chat Function in REST Server Tests

## Problem
Currently, `test_process_ok` in `test_rest_server.py` calls the full NotionAgent through the `/api/v1/process` endpoint. This makes the test slow, unreliable, and dependent on the entire agent infrastructure.

## Goal
Mock the `chat` function in REST server tests to provide predictable responses without running the full agent, making tests faster and more reliable.

## Implementation Plan

### 1. Mock Strategy
- Use pytest's `monkeypatch` or `unittest.mock.patch` to mock the `chat` function
- Mock should be applied at the module level where `chat` is imported in `rest_server.py`
- Return predictable, controlled responses from the mock

### 2. Test Structure Changes

#### Option A: Use pytest monkeypatch (Recommended)
```python
def test_process_ok_mocked(client, monkeypatch):
    # Mock the chat function to return a predictable response
    def mock_chat(loop=False, user_prompt=""):
        return "Mocked response for testing"
    
    monkeypatch.setattr("Agents.NotionAgent.launcher.rest_server.chat", mock_chat)
    
    r = client.post("/api/v1/process", json={"input": "Hello"})
    assert r.status_code == HTTPStatus.OK
    assert r.get_json()["result"] == "Mocked response for testing"
```

#### Option B: Use unittest.mock.patch decorator
```python
@patch('Agents.NotionAgent.launcher.rest_server.chat')
def test_process_ok_mocked(mock_chat, client):
    mock_chat.return_value = "Mocked response for testing"
    
    r = client.post("/api/v1/process", json={"input": "Hello"})
    assert r.status_code == HTTPStatus.OK  
    assert r.get_json()["result"] == "Mocked response for testing"
```

### 3. Test Scenarios to Cover

#### Happy Path Tests
- Mock returns successful response string
- Verify correct HTTP status code (200)
- Verify response JSON structure contains "result" field
- Verify mock is called with correct parameters (`loop=False`, `user_prompt=input_text`)

#### Error Handling Tests  
- Mock raises exception to test error handling
- Verify 500 status code and error message format
- Test different exception types (ValueError, RuntimeError, etc.)

#### Edge Cases
- Mock returns empty string
- Mock returns very long response
- Mock returns response with special characters/formatting

### 4. File Changes Required

#### `test_rest_server.py`
- Add import for mocking framework (`from unittest.mock import patch` or use pytest monkeypatch)
- Rename current `test_process_ok` to `test_process_ok_integration` (keep for integration testing)
- Add new `test_process_ok_mocked` with mocked chat function
- Add additional test methods for different mock scenarios

#### Optional: Test Utilities
- Consider creating a test utility function for common mock setups
- Could create fixtures for different mock response types

### 5. Benefits
- **Speed**: Tests run much faster without full agent initialization
- **Reliability**: No dependency on external services or complex agent state
- **Isolation**: Pure unit testing of REST server logic
- **Predictability**: Known inputs/outputs make assertions straightforward
- **Coverage**: Can test error scenarios that might be hard to trigger with real agent

### 6. Considerations
- Keep at least one integration test (`test_process_ok_integration`) to verify end-to-end functionality
- Mock should match the actual `chat` function signature exactly
- Consider parametrized tests to cover multiple input/output scenarios efficiently
- Document which tests are unit tests (mocked) vs integration tests (real agent)

### 7. Implementation Order
1. Add mocked version of `test_process_ok` 
2. Verify mocked test passes
3. Add error scenario tests with mocked exceptions
4. Rename original test to `test_process_ok_integration`, then comment it out
5. Update test documentation/comments to distinguish unit vs integration tests

## Success Criteria
- Tests run in < 1 second instead of several seconds
- All test scenarios pass consistently
- Mock accurately simulates chat function interface
- Maintains at least one integration test for end-to-end verification 