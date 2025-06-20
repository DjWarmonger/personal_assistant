# Docker Containerization Issues and Solutions Report

## Overview
Report documenting issues encountered during NotionAgent REST server containerization (June 19, 2025), their solutions, and prevention guidelines for future containerization efforts.

## Issues Encountered

### Issue 1: Missing Python Dependencies (termcolor, Pillow)

#### Problem
Container in restart loop with `ModuleNotFoundError: No module named 'termcolor'` and `ModuleNotFoundError: No module named 'PIL'`

#### Root Cause Analysis
1. **termcolor**: Listed in `common/pyproject.toml` but not properly installed during Docker build
2. **Pillow**: Used unconditionally in `common/src/tz_common/utils.py` but not included in any requirements file
3. **Build Process**: tz_common package installation wasn't propagating dependencies correctly

#### Solution Applied
```diff
# In Agents/NotionAgent/requirements.txt
+ termcolor>=2.0.0
+ Pillow>=9.0.0
```

```diff
# In Agents/NotionAgent/Dockerfile  
- RUN pip install -e ./tz_common
+ RUN cd ./tz_common && pip install -e .
```

#### Error Symptoms
- Container status: `Restarting (1) X seconds ago`
- Logs: Repeated import errors for termcolor/PIL
- Health check: Failing

#### Prevention Guidelines
1. **Audit All Imports**: Scan all source files for unconditional imports before containerization
2. **Explicit Dependencies**: Include all transitive dependencies explicitly in requirements.txt
3. **Build Context**: Ensure proper working directory when installing editable packages
4. **Dependency Testing**: Test import chains in isolated environment before container build

### Issue 2: Environment Variables Not Passed to Container

#### Problem
Container failing with OpenAI API key validation errors even after dependency fixes

#### Root Cause Analysis
Application expected environment variables (OpenAI API keys, Notion tokens) but docker-compose wasn't configured to pass them

#### Solution Applied
```diff
# In Agents/NotionAgent/docker_compose.yaml
+ env_file:
+   - .env
  environment:
    - PYTHONPATH=/app:/app/tz_common
```

#### Error Symptoms
- ValidationError in ChatOpenAI initialization
- Missing API key errors
- Application startup failure after successful dependency loading

#### Prevention Guidelines
1. **Environment Audit**: Document all required environment variables before containerization
2. **Local Testing**: Test with minimal environment variables to identify requirements
3. **Docker Compose First**: Configure environment passing early in the containerization process
4. **Documentation**: Maintain clear list of required environment variables in setup docs

### Issue 3: Misleading Error Messages During Debugging

#### Problem
Initial error showed as `ModuleNotFoundError: No module named 'termcolor'` but actual failure was later in the import chain (PIL)

#### Root Cause Analysis
Python import system fails fast - when `tz_common/__init__.py` imports modules, first failure stops entire chain, masking later issues

#### Investigation Process
1. Tested individual imports: `docker run --rm image python -c "import termcolor"`
2. Tested specific failing import: `docker run --rm image python -c "from tz_common.logs import log"`  
3. Discovered real error: `ModuleNotFoundError: No module named 'PIL'`

#### Prevention Guidelines
1. **Systematic Testing**: Test imports individually rather than relying on application startup
2. **Import Chain Analysis**: Map out import dependencies before containerization
3. **Isolated Testing**: Use `docker run --rm` for quick import testing during debugging
4. **Root Cause Focus**: Don't stop at first error - investigate the complete import chain

### Issue 4: Docker Build Caching Interference  

#### Problem
Even after fixing dependencies, container still showed old errors due to Docker layer caching

#### Root Cause Analysis
Docker was reusing cached layers that contained old dependency installations

#### Solution Applied
```bash
# Force complete rebuild
docker compose -f Agents/NotionAgent/docker_compose.yaml build --no-cache
```

#### Prevention Guidelines
1. **Cache Awareness**: Understand which changes invalidate Docker cache layers
2. **Clean Rebuilds**: Use `--no-cache` when debugging dependency issues
3. **Layer Optimization**: Structure Dockerfile to minimize cache invalidation
4. **Verification**: Always test with fresh builds when changing dependencies

### Issue 5: Static Status Displays in Dashboard

#### Problem
Dashboard status boxes showed static text that never updated, making debugging difficult

#### Root Cause Analysis
Status checking functions were called once in Marimo cell execution, not reactive to user interaction

#### Solution Applied
```python
# Split into separate reactive cells
@app.cell(hide_code=True)
def _(mo):
    status_refresh_button = mo.ui.button(label="Refresh Status")
    status_refresh_button
    return (status_refresh_button,)

@app.cell(hide_code=True) 
def _(check_container_status, check_server_health, mo, status_refresh_button):
    # Get button value to make this cell reactive
    _ = status_refresh_button.value
    
    # Get current status (updated each time button is clicked)
    server_status = check_server_health()
    container_status = check_container_status()
    # ... display logic
```

#### Prevention Guidelines
1. **Reactive Design**: Make monitoring UIs reactive from the start
2. **Manual Refresh**: Provide manual refresh options for debugging scenarios  
3. **Real-time Updates**: Consider periodic automatic updates for production monitoring
4. **User Feedback**: Ensure users can trigger status updates when needed

## Best Practices Derived

### Pre-Containerization Checklist
1. **Dependency Audit**
   - [ ] Map all import dependencies recursively
   - [ ] Identify system dependencies (PIL requires build tools)
   - [ ] Test imports in minimal environment
   - [ ] Document all environment variables required

2. **Build Strategy**
   - [ ] Start with explicit requirements.txt rather than relying on pyproject.toml propagation
   - [ ] Use multi-stage builds for complex dependencies
   - [ ] Test editable package installation paths
   - [ ] Plan for development vs production variations

3. **Testing Approach**
   - [ ] Test individual components before full application
   - [ ] Use `docker run --rm` for quick verification
   - [ ] Build monitoring/debugging tools early
   - [ ] Document successful build and run commands

### Debugging Methodology
1. **Systematic Isolation**: Test components individually
2. **Cache Awareness**: Rebuild without cache when debugging
3. **Error Chain Analysis**: Follow import chains to root cause
4. **Environment Verification**: Confirm all external dependencies available

### Future Containerization Projects
1. **Early Monitoring**: Build status checking into development workflow
2. **Dependency Explicit**: Don't rely on transitive dependency resolution
3. **Version Pinning**: Pin all dependency versions for reproducibility
4. **Documentation**: Maintain clear setup and troubleshooting guides

## Commands Reference

### Essential Debugging Commands
```bash
# Force clean rebuild
docker compose -f path/to/docker_compose.yaml down
docker compose -f path/to/docker_compose.yaml build --no-cache
docker compose -f path/to/docker_compose.yaml up -d

# Quick import testing
docker run --rm image-name python -c "import module_name; print('Success')"

# Container status and logs
docker ps
docker logs container-name --tail 20

# Environment testing
docker run --rm image-name python -c "import os; print(os.environ.get('VAR_NAME'))"
```

### File Structure Validation
```bash
# Check container file structure  
docker run --rm image-name ls -la /app/
docker run --rm image-name python -c "import sys; print('\\n'.join(sys.path))"
```
