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
- [x] Auto-refresh timer implemented (Phase 4 complete)
- [x] Status display with proper layout (Phase 4 complete)
- [x] Toggle successfully switches between local and server execution
- [❌] Docker container can be launched/stopped from dashboard (buttons not working)
- [❌] Container status accurately reflected in UI (depends on container launch)
- [ ] Server mode produces same results as local mode (needs container launch fix)
- [ ] Clear error handling for all failure scenarios (partially done)
- [ ] Performance metrics displayed for mode comparison (basic timing added)

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

### ✅ Phase 2 Complete (Backend Integration)
**Completed Features:**
- Modified `run_chat()` function to support both local and server modes
- Added `aiohttp` for async HTTP requests to REST server
- Implemented `send_to_server()` function with proper error handling
- Added mode switching logic that respects the toggle switch
- Enhanced results display with mode indicators (🖥️ for server, 💻 for local)
- Added execution time display in tab titles
- Fixed Docker command paths to run from project root with full compose file path
- Updated Docker commands to use `docker compose` instead of `docker-compose`
- Increased timeout for container launch to 2 minutes (build can take time)

**Files Modified:**
- `launcher/dashboard.py`: Added server communication, mode switching, and fixed Docker paths

### ✅ Phase 3 Complete (Status Monitoring & UX)
**Completed Features:**
- Fixed Docker container management - buttons now work properly
- Removed manual refresh button and extra status labels
- Added automatic status refresh every 5 seconds using `mo.ui.refresh()`
- Integrated status display with button results in single panel
- Added visual indicators (✅❌⏱️) for better UX
- Status updates automatically when buttons are clicked
- Simplified UI layout - removed redundant components

**Files Modified:**
- `launcher/dashboard.py`: Fixed button handling, added auto-refresh, simplified status display

### ✅ Phase 4 Complete (GUI Implementation)
**Completed Features:**
- All UI components properly implemented and positioned
- Auto-refresh timer integrated with main UI layout
- Status display with horizontal layout (status + timer control)
- Timer merged with main panel cell for better organization
- Status cell refreshes automatically every 5 seconds
- Clean UI layout with all components working

**Files Modified:**
- `launcher/dashboard.py`: Final UI layout and timer integration

### ❌ Known Issues (Not Resolved)
**Container Launch Issues:**
- Docker container launch buttons do not work - no visible action when clicked
- Container management functions may not be executing properly
- No logs appear in a file when buttons are pressed
- Need to debug button event handling and subprocess execution

**Next Steps for Resolution:**
- Debug why button clicks are not triggering container functions
- Check if logs are being output to correct location (Marimo vs terminal)
- Test container launch functions independently
- Verify subprocess execution and error handling
- May need to add explicit logging to Marimo output instead of console

### 🔍 Log Visibility Issue (NEW)

**Observed Problem**  
No log entries from button actions are visible either in the `logs/*.log` files or in the live dashboard output.

**Possible Causes**  
1. *Log-level filtering* – `dashboard.py` sets the logger to `LogLevel.COMMON` (15).
   • `log.flow()` and `log.debug()` emit levels 5 and 10, both **below** the active level, so they are silently discarded.  
2. *File-handler threshold* – the underlying `logging.FileHandler` is initialised at `DEBUG` (10). Messages with level 5 (`FLOW`) never reach the file even if the logger level is lowered.  
3. *Missing stream handler* – the custom logger only writes to file. Console output is produced with a plain `print()`, which Marimo does **not** capture for background or asynchronous tasks, so nothing appears inside the dashboard.  
4. *Wrong working directory* – the logger creates the `logs` folder relative to the current working directory. When the dashboard is started from `Agents/NotionAgent/launcher`, log files end up in that sub-folder, not in the project-root `logs/`, giving the impression that they are missing.  
5. *Async execution context* – button callbacks run in new threads / event loops, so even if `print()` is executed it may not propagate to the cell that the user is watching.

**Proposed Solutions**  
- ✅ **FIXED**: Set the lowest log level at the start of the dashboard:  
  ```python
  log.set_log_level(LogLevel.FLOW)
  log.set_file_log_level(LogLevel.FLOW)  # NEW METHOD
  ```  
- ✅ **FIXED**: Added `set_file_log_level()` method to `logs.py` to control file handler level separately from console level.  
- Add a `logging.StreamHandler` (or custom wrapper) pointing to `sys.stdout` so Marimo can capture standard output.  
- Provide the logger with an absolute path, e.g. `project_root / "logs"` to avoid scattered log folders.  
- Create a dedicated *Log Window* component in the dashboard (e.g. `mo.ui.text_area`) that is updated via a reactive variable whenever a log entry is produced.  
- For quick debugging wrap button bodies with `log.common()` (level 15) or `log.user()` (20) to confirm pipeline end-to-end before refining the levels.

**Files Modified for Log Fix:**
- `common/src/tz_common/logs.py`: Added `set_file_log_level()` method and stored file handler reference
- `launcher/dashboard.py`: Added call to `log.set_file_log_level(LogLevel.FLOW)` and debug logging for button states

**Current Status:** 
- ✅ FLOW level logs now appear in log files and Marimo panels
- 🔄 **TESTING**: Button reactivity fix - moved Docker buttons to dedicated cell (matching refresh button pattern)
- ❌ Button values were showing as None despite clicks
- **New Fix Applied**: Created Docker buttons in their own dedicated cell, exactly matching the working refresh button pattern

## Dependencies & Prerequisites
- Docker and docker-compose installed on system
- Existing REST server functional
- Marimo dashboard currently working
- Network access to localhost:8000 when container running
- **Phase 1**: ✅ All UI components implemented and functional 