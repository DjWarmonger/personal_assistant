# Dashboard Server Mode Integration

## Overview
Add functionality to the Marimo dashboard to optionally send chat requests to a dockerized REST server instead of running chat locally, with Docker container management controls.

## Features
1. **Mode Toggle**: Switch between local `chat()` calls and REST server requests (`http://localhost:8000/api/v1/process`)
2. **Docker Management**: Launch/stop container buttons with real-time status monitoring (5s auto-refresh)  
3. **Server Communication**: Async HTTP with health checks, error handling, and performance metrics

## Implementation Status

### ✅ Completed (100%)
- **UI**: Mode toggle, Docker buttons, auto-refresh status (5s), visual indicators
- **Backend**: Dual-mode `run_chat()`, async server communication, error handling
- **Docker**: Dedicated `DockerManager` class with 11 integration tests
- **Monitoring**: Real-time health checks, performance metrics in tab titles
- **Logging**: Fixed visibility issues, proper level configuration
- **State Management**: Fixed Marimo button state management with proper `mo.state()` patterns

### ✅ Resolved: Marimo State Management
**Solution**: Implemented proper Marimo state management patterns using `mo.state()` with getter/setter functions and `on_click` handlers  
**Result**: Docker buttons work correctly, state persists across refreshes, no more AttributeError  
**Documentation**: Created `.notes/marimo-button-state-fix.md` with implementation details and prevention strategies

## Technical Details
- **Dependencies**: `aiohttp`, `subprocess`, custom logging from `tz_common.logs`
- **Configuration**: Server `localhost:8000`, 5min request timeout, 5s status refresh, 2min container launch timeout
- **Error Handling**: Connection timeouts, server unavailable scenarios, Docker failures, graceful degradation
- **Files**: `dashboard.py` (main), `docker_manager.py` (NEW), `logs.py` (enhanced), test files (NEW)

## Final Implementation
1. **Marimo State Management**: Proper `mo.state()` usage with getter/setter functions
2. **Button Click Handlers**: `on_click=lambda _: handler()` pattern with state updates
3. **Reactive Cells**: Automatic re-execution when referenced state changes
4. **Complete Integration**: All features working together seamlessly

## Status: ✅ COMPLETE
All functionality implemented, tested, and working correctly. Marimo UI state management resolved. 