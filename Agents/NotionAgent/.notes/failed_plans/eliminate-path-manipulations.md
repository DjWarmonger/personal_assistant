# Eliminate Path Manipulations - NotionAgent Refactoring Plan

## Overview
Refactor NotionAgent to follow proper Python packaging standards using pyproject.toml and src/ layout, eliminating manual path manipulations while maintaining full backward compatibility with existing commands in setup.md.

## Current Problems
- Manual path manipulations in launcher files (rest_server.py, chat.py)
- Import errors when running from different directories
- Non-standard project structure
- Dependency on manual PYTHONPATH manipulation

## Goals
1. **Eliminate all path manipulations** from launcher files
2. **Maintain 100% backward compatibility** with existing setup.md commands
3. **Follow Python best practices** using proper packaging
4. **Enable clean imports** without sys.path modifications
5. **Improve maintainability** and reduce import complexity

## Backward Compatibility Requirements

### Commands That MUST Continue Working
From setup.md, these commands must remain functional:

#### Interactive Chat Mode
```bash
conda activate services
python -m Agents.NotionAgent.launcher.chat
```

#### REST Server Mode
```bash
conda activate services
python Agents/NotionAgent/launcher/rest_server.py
```

#### Testing Commands
```bash
conda activate services
python -m pytest Agents/NotionAgent/tests -v
python -m pytest Agents/NotionAgent/tests/test_rest_server.py -v
```

## Implementation Strategy

### Phase 1: Prepare Dependencies
1. **Install tz_common properly**
   ```bash
   cd common
   pip install -e .
   ```

2. **Update NotionAgent pyproject.toml dependencies**
   - Add `tz-common` as dependency
   - Add `flask` as dependency
   - Ensure all required packages are listed

3. **Install NotionAgent in development mode**
   ```bash
   cd Agents/NotionAgent
   pip install -e .
   ```

### Phase 2: Clean Up Imports (No Structure Changes)
1. **Remove path manipulations from launcher files**
   - `launcher/rest_server.py`
   - `launcher/chat.py`
   - Any other files with sys.path modifications

2. **Use proper imports**
   - Replace `from chat import chat` with proper module imports
   - Use absolute imports for tz_common
   - Leverage installed packages instead of path hacks

3. **Test backward compatibility**
   - Verify all setup.md commands still work
   - Run all tests to ensure functionality

## Detailed Implementation Plan

### Step 1: Update pyproject.toml
```toml
[project]
name = "notion-agent"
version = "0.1.0"
dependencies = [
    "aiohttp",
    "python-dotenv", 
    "pydantic>=1.10.8,<2.0.0",
    "pytest",
    "pytest-asyncio",
    "flask",
    "tz-common",  # Add tz-common dependency
    # Add other missing dependencies
]

[tool.setuptools]
packages = ["Agent", "operations", "launcher"]
# Note: Keep current structure to maintain compatibility
```

### Step 2: Clean Up rest_server.py
**Before:**
```python
import sys
from pathlib import Path

# Reuse path setup from chat.py
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

# Add launcher directory to path
launcher_dir = Path(__file__).parent.absolute()
if str(launcher_dir) not in sys.path:
	sys.path.insert(0, str(launcher_dir))

from chat import chat
```

**After:**
```python
from flask import Flask, request, jsonify
from http import HTTPStatus

from .chat import chat  # Clean relative import
# OR
from launcher.chat import chat  # Absolute import if installed properly
```

### Step 3: Clean Up chat.py
Remove any path manipulations and use proper imports:
```python
from tz_common.logs import log
from tz_common.langchain_wrappers import add_timestamp

from Agent.plannerGraph import planner_runnable
from Agent.graph import notion_agent, langfuse_handler
```

### Step 4: Update __init__.py Files
Ensure all directories have proper `__init__.py` files:
- `Agents/NotionAgent/__init__.py`
- `Agents/NotionAgent/Agent/__init__.py`
- `Agents/NotionAgent/operations/__init__.py`
- `Agents/NotionAgent/launcher/__init__.py`

### Step 5: Test Compatibility Matrix

| Command | Status | Notes |
|---------|--------|-------|
| `python -m Agents.NotionAgent.launcher.chat` | ✅ Must work | Module execution |
| `python Agents/NotionAgent/launcher/rest_server.py` | ✅ Must work | Direct file execution |
| `python -m pytest Agents/NotionAgent/tests -v` | ✅ Must work | Test execution |
| `python -m pytest Agents/NotionAgent/tests/test_rest_server.py -v` | ✅ Must work | Specific test |

## Risk Mitigation

### Testing Strategy
1. **Unit Tests**: All existing tests must pass
2. **Integration Tests**: Manual testing of all setup.md commands
3. **Import Tests**: Verify clean imports work from different directories
4. **CLI Tests**: Test both module and direct execution modes

### Fallback Plan
If any compatibility issues arise:

1. Revert to current state
2. Implement minimal fixes only (Option 2 from previous analysis)
3. Document any command changes required

## Success Criteria

### Must Have
- ✅ All setup.md commands work unchanged
- ✅ All tests pass
- ✅ No path manipulations in any launcher file
- ✅ Clean imports throughout codebase
- ✅ Proper dependency management

### Nice to Have
- ✅ Improved error messages for missing dependencies
- ✅ Cleaner project structure
- ✅ Better documentation of dependencies

## Dependencies and Prerequisites

### Before Starting
1. Ensure `services` conda environment is active
2. Install tz_common: `cd common && pip install -e .`
3. Verify all current functionality works
4. Create git branch for changes

## Timeline and Phases

### Phase 1 (Immediate): Dependency Setup
- Install dependencies properly
- No code changes yet

### Phase 2 (Main Work): Clean Up Imports  
- Remove path manipulations
- Update imports
- Test compatibility

### Phase 3 (Validation): Comprehensive Testing
- Test all setup.md commands
- Run full test suite
- Verify functionality

## Post-Implementation

### Documentation Updates
- Update setup.md if any commands change (should not be needed)
- Update .notes/notion-agent-testing-commands.md if needed
- Document the cleaner import structure