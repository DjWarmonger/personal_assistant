### 2. Incomplete Dependency Declarations

**Issue**: Missing dependencies in package declarations (e.g., `termcolor` not listed in tz_common)

**Root Cause**: 
- Dependencies working in development environment but not declared in pyproject.toml
- Package installation relies on transitive dependencies from other packages
- No systematic dependency auditing process

**Impact**: 
- Runtime failures in clean environments (Docker, CI/CD)
- Fragile builds that break when other packages update
- Difficult to reproduce environments

### 3. Environment-Specific Dependency Resolution

**Issue**: Packages that work in conda environment fail in Docker with same versions

**Root Cause**: 
- Different Python versions between environments
- Different dependency resolution algorithms (conda vs pip)
- Hidden system dependencies or pre-installed packages

**Impact**: 
- Inconsistent behavior across deployment targets
- Difficult debugging and troubleshooting
- Unreliable containerization