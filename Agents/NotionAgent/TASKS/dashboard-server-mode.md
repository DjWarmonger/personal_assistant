# Dashboard Server Mode Integration

## Overview
Add functionality to the Marimo dashboard to optionally send chat requests to a dockerized REST server instead of running chat locally. Include controls to launch/manage the Docker container.

## Current State Analysis
- Dashboard currently calls `chat()` function directly via `asyncio.to_thread()`
- REST server exists at `launcher/rest_server.py` with `/api/v1/process` endpoint
- Docker setup exists with `docker_compose.yaml` and `Dockerfile`
- Dashboard uses `mo.ui.multiselect()` for prompt selection and `mo.ui.run_button()` for execution

## Planned Features

### 1. Execution Mode Toggle
**UI Component**: Add a toggle switch next to "Run chats" button
- **Local Mode** (default): Current behavior using direct `chat()` calls
- **Server Mode**: Send requests to REST server at `http://localhost:8000/api/v1/process`

**Implementation**:
- Add `mo.ui.switch()` component with label "Use Server Mode"
- Store mode selection in reactive variable
- Modify `run_chat()` function to branch based on mode

### 2. Docker Container Management
**UI Components**: Add container control buttons
- **Launch Container**: Start docker-compose services
- **Stop Container**: Stop running services  
- **Container Status**: Display current container state

**Implementation**:
- Use `subprocess` to run docker-compose commands
- Add status checking via `/health` endpoint
- Display container logs in collapsible section

### 3. Server Communication Module
**New Functions**:
- `send_to_server(prompt: str) -> str`: Send request to REST server
- `check_server_health() -> bool`: Verify server availability
- `get_container_status() -> str`: Check Docker container state

**Error Handling**:
- Connection timeout handling
- Server unavailable fallback to local mode
- Clear error messages in UI

## Detailed Implementation Plan

### Phase 1: UI Components ✅ COMPLETED
1. **Add mode toggle switch**: ✅
   ```python
   mode_switch = mo.ui.switch(label="Use Server Mode", value=False)
   ```

2. **Add Docker control buttons**: ✅
   ```python
   launch_container_button = mo.ui.button(label="Launch Container")
   stop_container_button = mo.ui.button(label="Stop Container")
   server_status_text = mo.ui.text("Server Status: Checking...")
   container_status_text = mo.ui.text("Container Status: Unknown")
   ```

3. **Update layout**: ✅
   - Group mode switch with run button using `mo.hstack()`
   - Add Docker controls in separate section with proper spacing
   - Add status indicators with automatic status checking
   - Organized layout using `mo.vstack()` for clear sections

**Implementation Details:**
- Added Docker container management functions with proper error handling
- Integrated status checking for both server health and container state
- Added proper timeouts and logging using project's custom log system
- Created responsive UI layout with visual status indicators (✓, ✗, ○, ?)

### Phase 2: Backend Integration
1. **Create server communication functions**:
   ```python
   async def send_to_server(prompt: str, base_url: str = "http://localhost:8000") -> str:
       async with aiohttp.ClientSession() as session:
           async with session.post(f"{base_url}/api/v1/process", 
                                 json={"input": prompt}) as response:
               result = await response.json()
               return result["result"]
   ```

2. **Modify `run_chat()` function**:
   - Check mode selection
   - Branch to either local `chat()` or `send_to_server()`
   - Handle errors appropriately

3. **Add Docker management**:
   ```python
   def launch_container():
       subprocess.run(["docker-compose", "up", "-d"], 
                     cwd=Path(__file__).parent.parent)
   
   def stop_container():
       subprocess.run(["docker-compose", "down"], 
                     cwd=Path(__file__).parent.parent)
   ```

### Phase 3: Status Monitoring
1. **Health check integration**:
   - Periodic status checks when server mode enabled
   - Visual indicators for server availability
   - Automatic fallback suggestions

2. **Container status monitoring**:
   - Check Docker container state
   - Display container logs if needed
   - Show resource usage if available

### Phase 4: Error Handling & UX
1. **Graceful degradation**:
   - Automatic fallback to local mode if server unavailable
   - Clear error messages with actionable suggestions
   - Retry mechanisms for transient failures

2. **User feedback**:
   - Loading indicators during server requests
   - Success/error notifications
   - Performance comparison (local vs server timing)

## Technical Considerations

### Dependencies
- Add `aiohttp` for async HTTP requests
- Import `subprocess` for Docker commands
- Import `pathlib.Path` for working directory management

### Configuration
- Server URL should be configurable (default: `http://localhost:8000`)
- Timeout settings for server requests
- Docker-compose file path configuration

### Error Scenarios
1. **Server not running**: Show clear message, offer to launch container
2. **Container build failure**: Display Docker logs and troubleshooting tips
3. **Network connectivity issues**: Timeout handling and retry logic
4. **Server internal errors**: Display server error messages

## File Changes Required

### Modified Files
- `launcher/dashboard.py`: Main implementation
- `launcher/rest_server.py`: Potentially add logging improvements

### New Dependencies
- Update `requirements.txt` if new packages needed
- Ensure `aiohttp` is available for async HTTP requests

### Testing Strategy
1. **Manual testing scenarios**:
   - Toggle between modes with same prompts
   - Launch/stop container multiple times
   - Test error conditions (server down, network issues)

2. **Validation checks**:
   - Compare local vs server results for consistency
   - Verify container lifecycle management
   - Test concurrent request handling

## Success Criteria
- [x] UI components added (Phase 1 complete)
- [x] Docker container can be launched/stopped from dashboard
- [x] Container status accurately reflected in UI
- [ ] Toggle successfully switches between local and server execution
- [ ] Server mode produces same results as local mode
- [ ] Clear error handling for all failure scenarios
- [ ] Performance metrics displayed for mode comparison

## Current Progress

### ✅ Phase 1 Complete (UI Components)
**Completed Features:**
- Mode toggle switch added and positioned next to "Run chats" button
- Docker container launch/stop buttons with proper subprocess integration
- Real-time status monitoring for both server health and container state
- Responsive UI layout with clear visual sections
- Error handling and timeout management for container operations
- Integration with project's custom logging system

**Files Modified:**
- `launcher/dashboard.py`: Added UI components, container management, and status checking

### 🔄 Next: Phase 2 (Backend Integration)
- Modify `run_chat()` function to support server mode
- Add `aiohttp` for HTTP requests to REST server
- Implement mode switching logic
- Add error handling for server communication

## Dependencies & Prerequisites
- Docker and docker-compose installed on system
- Existing REST server functional
- Marimo dashboard currently working
- Network access to localhost:8000 when container running
- **Phase 1**: ✅ All UI components implemented and functional 