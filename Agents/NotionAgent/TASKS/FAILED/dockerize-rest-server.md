# Dockerize Notion REST Server Plan

## Overview
Plan to containerize the Notion REST server with all dependencies, including the tz_common library and NotionAgent system components.

## Current State Analysis

### Existing Files
- `launcher/rest_server.py` - Flask server using `chat()` function
- `docker_compose.yaml` - Contains only TODO comment
- `Dockerfile` - Contains only TODO comment  
- `tests/test_rest_server.py` - Basic tests for REST endpoints

### Dependencies Identified

#### Core Runtime Dependencies (from services environment)
1. **Web Framework**:
   - Flask==3.0.3 (REST server)
   - Werkzeug==3.0.3 (WSGI utility)

2. **LangChain Ecosystem**:
   - langchain==0.2.6
   - langchain-community==0.2.6
   - langchain-core==0.2.11
   - langchain-openai==0.1.14
   - langchain-text-splitters==0.2.2
   - langgraph==0.1.5
   - langsmith==0.1.83

3. **OpenAI & AI Services**:
   - openai==1.35.10
   - langfuse==2.59.3

4. **Core Python Libraries**:
   - aiohttp==3.9.5
   - python-dotenv==1.0.1
   - pydantic==1.10.22 (v1 as required)
   - requests==2.32.3

5. **Local Packages** (editable installs):
   - notion_agent==0.1.0 (current project)
   - tz-common==0.9.0 (dependency)

#### Testing Dependencies
- pytest==8.2.2
- pytest-asyncio==0.25.0

#### System Dependencies
- Standard library modules: sys, pathlib, os
- JSON handling, HTTP status codes

#### tz_common Internal Dependencies
- Custom logging system (`tz_common.logs`)
- LangChain wrappers (`tz_common.langchain_wrappers`) 
- Task management (`tz_common.tasks`)
- Actions system (`tz_common.actions`)
- Custom UUID handling (`tz_common.CustomUUID`)

#### NotionAgent System Dependencies
- `Agent.plannerGraph.planner_runnable`
- `Agent.graph.notion_agent, langfuse_handler`
- All Agent modules (agentTools, agentState, etc.)
- Operations modules (blocks, notion, utilities)

## Implementation Plan

### Phase 1: Dockerfile Creation
Create multi-stage Dockerfile following PROJECT_TEMPLATE guidelines:

1. **Base Stage**: 
   - Use Python 3.12-slim
   - Set working directory to `/app`

2. **Dependencies Stage**:
   - Copy and install tz_common from source
   - Install NotionAgent dependencies from pyproject.toml
   - Handle Python path setup for imports

3. **Runtime Stage**:
   - Copy NotionAgent source code (maintaining directory structure)
   - Keep rest_server.py in launcher/ directory
   - Set up proper Python path
   - Expose port 8000

### Phase 2: tz_common Integration Strategy
**Option A: Copy Source (Recommended)**
- Copy `common/src/tz_common` into container
- Install in editable mode with `pip install -e`
- Maintain development workflow compatibility

**Option B: Build Wheel**
- Build tz_common wheel during Docker build
- Install as package
- More production-ready but complex

### Phase 3: Docker Compose Configuration
Update `docker_compose.yaml` with:

```yaml
version: "3.9"
services:
  notion-rest-server:
    build: .
    container_name: notion-rest-server
    ports:
      - "8000:8000"
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs  # Persistent log storage
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s  # Longer start period due to complex dependencies
    environment:
      - PYTHONPATH=/app:/app/tz_common
```

### Phase 4: File Structure in Container
```
/app/
├── tz_common/              # Copied from common/src/tz_common
├── Agent/                  # NotionAgent modules
├── operations/             # NotionAgent operations
├── launcher/               # All launch scripts
│   ├── chat.py            # Chat functionality
│   ├── rest_server.py     # Main REST server file (keep in launcher/)
│   └── other launchers... # Other entry points
└── logs/                   # Persistent log directory
```

### Phase 5: Python Path Management
Handle complex import structure:
- Set PYTHONPATH environment variable
- Ensure tz_common is importable
- Maintain compatibility with existing path setup in rest_server.py
- Keep rest_server.py in launcher/ directory to preserve current import logic

### Phase 5.1: Project Structure Decision
**Decision: Keep current structure, do NOT move rest_server.py to root**

**Rationale:**
1. **Existing Import Logic**: Current rest_server.py uses path manipulation assuming launcher/ location:
   ```python
   project_root = Path(__file__).parent.parent.parent.absolute()  # 3 levels up
   launcher_dir = Path(__file__).parent.absolute()                # launcher dir
   from chat import chat  # Direct import from same directory
   ```

2. **Logical Organization**: launcher/ directory contains all entry point scripts
3. **Minimal Changes**: No code refactoring required
4. **Consistency**: Follows established NotionAgent patterns

**Docker Implications:**
- Use `CMD ["python", "launcher/rest_server.py"]` in Dockerfile
- Maintain full directory structure in container
- No import path changes needed

### Phase 6: Requirements File Content
Create `requirements.txt` with core dependencies:

```txt
# Web Framework
Flask==3.0.3
Werkzeug==3.0.3

# LangChain Ecosystem
langchain==0.2.6
langchain-community==0.2.6
langchain-core==0.2.11
langchain-openai==0.1.14
langchain-text-splitters==0.2.2
langgraph==0.1.5
langsmith==0.1.83

# AI Services
openai==1.35.10
langfuse==2.59.3

# Core Libraries
aiohttp==3.9.5
python-dotenv==1.0.1
pydantic==1.10.22
requests==2.32.3

# Development/Testing (optional)
pytest==8.2.2
pytest-asyncio==0.25.0
```

## Implementation Tasks

### Task 1: Create Requirements File ✅ COMPLETED
- [x] Create `requirements.txt` with pinned versions from services environment
- [x] Separate development dependencies from runtime dependencies (`requirements-dev.txt`)
- [x] Ensure compatibility with pydantic v1 requirement

**Files Created:**
- `requirements.txt` - Runtime dependencies for Docker container
- `requirements-dev.txt` - Development dependencies (includes runtime via -r)

### Task 2: Create Dockerfile ✅ COMPLETED
- [x] Write multi-stage Dockerfile based on PROJECT_TEMPLATE
- [x] Handle tz_common source copying and installation
- [x] Set up proper Python environment with requirements.txt
- [x] Configure port exposure and working directory
- [x] Set CMD to run `python launcher/rest_server.py` (maintain current structure)

**Implementation Notes:**
- Used Python 3.11-slim to avoid Pydantic v2 conflicts
- Fixed tz_common directory structure with proper src/ layout
- Added missing termcolor dependency to tz_common pyproject.toml
- Excluded tests from production container

### Task 3: Update Docker Compose ✅ COMPLETED
- [x] Replace TODO in docker_compose.yaml
- [x] Add persistent volume for logs
- [x] Configure health checks
- [x] Set environment variables

**Files Updated:**
- `docker_compose.yaml` - Complete configuration with build context from project root
- Added .dockerignore for optimized builds

### Task 4: Test Integration ✅ PARTIALLY COMPLETED
- [x] Build Docker image locally
- [x] Verify tz_common imports work
- [x] Fix missing dependencies (termcolor, Pillow)
- [x] Configure environment variables (.env file)
- [x] Resolve Docker build and dependency issues
- [ ] Fix LangChain/OpenAI compatibility issue
- [ ] Test REST endpoints in container
- [ ] Test chat functionality

**Status:**
- Docker image builds successfully (~750MB, Python 3.11)
- Container loads and initializes most components successfully
- All core dependency imports resolved (tz_common, termcolor, Pillow)
- Database and cache initialization working
- **Current Issue**: LangChain/OpenAI version compatibility error preventing server startup

### Task 5: Documentation ✅ COMPLETED
- [x] Update README.md with Docker instructions
- [x] Document build and run commands
- [x] Add troubleshooting section

**Documentation Created:**
- `.notes/docker-launch-guidelines.md` - Comprehensive Docker operations guide
- `TASKS/version-migration-analysis.md` - Dependency conflict analysis and solutions
- Updated PROJECT_TEMPLATE files with lessons learned

## Issues Encountered & Resolutions

### 1. Missing Dependencies ✅ RESOLVED
**Issue**: Container restart loop due to missing `termcolor` and `Pillow` dependencies
- `ModuleNotFoundError: No module named 'termcolor'`
- `ModuleNotFoundError: No module named 'PIL'`

**Root Cause**: 
- tz_common pyproject.toml dependencies weren't being installed properly during Docker build
- utils.py imports PIL unconditionally but Pillow wasn't in requirements

**Resolution**:
- Added explicit `termcolor>=2.0.0` to requirements.txt
- Added explicit `Pillow>=9.0.0` to requirements.txt
- Fixed tz_common installation in Dockerfile with proper working directory

### 2. Environment Variables Missing ✅ RESOLVED
**Issue**: Application failing to initialize due to missing OpenAI API keys
**Resolution**: Added `.env` file configuration to docker-compose.yaml

### 3. LangChain/OpenAI Compatibility ⚠️ CURRENT ISSUE
**Issue**: `Client.__init__() got an unexpected keyword argument 'proxies'`
**Status**: Container initializes successfully but fails at ChatOpenAI setup
**Impact**: REST server doesn't start, health endpoint unavailable

**Analysis**: Version compatibility issue between:
- langchain-openai==0.1.14 
- openai==1.35.10
- Likely related to OpenAI client API changes

### 4. Complex Import Structure ✅ RESOLVED
- NotionAgent uses dynamic path manipulation
- Multiple sys.path.insert() calls in different modules
- Current rest_server.py assumes launcher/ directory location
- Solution: Maintain current directory structure, set PYTHONPATH appropriately

### 5. tz_common Development Workflow ✅ RESOLVED
- Currently installed in editable mode for development
- Need to maintain development compatibility
- Solution: Use volume mounts for development, source copy for production

### 6. Log File Management ✅ RESOLVED
- Current system writes to local logs directory
- Need persistent storage in container
- Solution: Volume mount for logs directory

## Success Criteria

1. **Functional Container**: ⚠️ REST server builds and starts but fails due to LangChain compatibility
2. **Complete Dependencies**: ✅ All tz_common and NotionAgent imports work
3. **Persistent Logs**: ✅ Log files survive container restarts
4. **Easy Deployment**: ✅ Single command deployment with docker-compose
5. **Development Friendly**: ✅ Support for development workflow with volume mounts

## Current Container Status

### ✅ Working Components
- Docker image builds successfully (~750MB)
- tz_common package installation and imports
- All Python dependencies resolved (termcolor, Pillow, etc.)
- Environment variable configuration
- Database and cache initialization
- Block management system loading
- Log system initialization

### ⚠️ Failing Component
- LangChain/OpenAI client initialization
- REST server startup (due to above failure)
- Health endpoint availability

### 🔧 Container Logs Summary
```
TZRag not available - missing dependencies  # Expected warning
Index loaded from disk                       # ✅ Working
Created index table                          # ✅ Working
Created favourites table                     # ✅ Working
Block cache loaded from disk                 # ✅ Working
ValidationError: Client.__init__() got an unexpected keyword argument 'proxies'
```

## Next Steps

### Immediate Priority
1. **Fix LangChain/OpenAI Compatibility**: 
   - Update OpenAI client version or modify ChatOpenAI initialization
   - Remove 'proxies' parameter if not supported in current OpenAI client version
   - Test compatibility between langchain-openai==0.1.14 and openai==1.35.10

### Dashboard Integration
2. **Dashboard Status Fixes**: ✅ COMPLETED
   - Fixed static status boxes with reactive refresh button
   - Added real-time container status checking
   - Status updates now work properly on button click

## Future Enhancements

1. **Multi-Environment Support**: Separate dev/prod configurations
2. **Secret Management**: Environment-based configuration
3. **Monitoring**: Add metrics and observability
4. **Scaling**: Support for multiple container instances

## Files Modified in This Session

### ✅ Fixed Files
- `Agents/NotionAgent/requirements.txt` - Added termcolor and Pillow
- `Agents/NotionAgent/docker_compose.yaml` - Added .env file configuration
- `Agents/NotionAgent/launcher/dashboard.py` - Fixed static status boxes
- `Agents/NotionAgent/Dockerfile` - Fixed tz_common installation path

### 📋 Commands for Container Management
```bash
# Stop and rebuild
docker compose -f Agents/NotionAgent/docker_compose.yaml down
docker compose -f Agents/NotionAgent/docker_compose.yaml build --no-cache
docker compose -f Agents/NotionAgent/docker_compose.yaml up -d

# Check status and logs
docker ps
docker logs notion-rest-server --tail 20
``` 