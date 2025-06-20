# Dashboard Server Mode Integration

## Overview
Add functionality to the Marimo dashboard to optionally send chat requests to a dockerized REST server instead of running chat locally, with Docker container management controls.

## Features
1. **Mode Toggle**: Switch between local `chat()` calls and REST server requests (`http://localhost:8000/api/v1/process`)
2. **Docker Management**: Launch/stop container buttons with real-time status monitoring (5s auto-refresh)  
3. **Server Communication**: Async HTTP with health checks, error handling, and performance metrics

## Implementation Status

### ✅ Completed (90%)
- **UI**: Mode toggle, Docker buttons, auto-refresh status (5s), visual indicators
- **Backend**: Dual-mode `run_chat()`, async server communication, error handling
- **Docker**: Dedicated `DockerManager` class with 39 passing tests (28 unit + 11 integration)
- **Monitoring**: Real-time health checks, performance metrics in tab titles
- **Logging**: Fixed visibility issues, proper level configuration

### 🔄 Current Blocker: Marimo State Management
**Issue**: Docker commands work correctly, but `mo.state()` usage causes `AttributeError: 'tuple' object has no attribute 'value'`  
**Impact**: Button results not displayed in UI, state doesn't persist across refreshes  
**Cause**: Incorrect understanding of Marimo's state management patterns

## Technical Details
- **Dependencies**: `aiohttp`, `subprocess`, custom logging from `tz_common.logs`
- **Configuration**: Server `localhost:8000`, 5min request timeout, 5s status refresh, 2min container launch timeout
- **Error Handling**: Connection timeouts, server unavailable scenarios, Docker failures, graceful degradation
- **Files**: `dashboard.py` (main), `docker_manager.py` (NEW), `logs.py` (enhanced), test files (NEW)

## Next Steps
1. **Research Marimo state management**: Understand correct `mo.state()` usage and button `on_click` patterns
2. **Fix button integration**: Apply correct Marimo patterns, ensure state persists across refreshes  
3. **Final verification**: Test complete workflow and error scenarios

## Status: 90% Complete
Core functionality implemented and tested. Only Marimo UI state management needs resolution. 