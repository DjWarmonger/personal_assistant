# NotionAgent Import Path Issues

## Issue: Absolute imports in test files causing ModuleNotFoundError

* Issue: Test files were using absolute imports starting with `Agents.NotionAgent` (e.g., `from Agents.NotionAgent.operations.blockCache import BlockCache`). This structure assumed NotionAgent was part of a larger Agents package, but it should work as a standalone project.

* Resolution: Changed absolute imports to relative imports in all test files:
  - Updated `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))` to `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))` 
  - Changed `from Agents.NotionAgent.operations.X` to `from operations.X`
  - Applied these changes consistently across all test files

* Prevention:
  - Use relative imports within a package (e.g., `from .blockCache import BlockCache`) to maintain modularity
  - Package modules should not assume their location in a larger project structure
  - Add proper `__init__.py` files to ensure Python recognizes the directory as a package

## Issue: Unnecessary sys.path manipulation for accessing tz_common

* Issue: Code in `notion_client.py` was adding the parent directory to sys.path to access `tz_common`, creating unnecessary path dependencies and making the code less portable.

* Resolution: 
  - Removed the line `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))` from `notion_client.py`
  - Verified that direct import of `tz_common.logs` works when `tz_common` is properly installed in the environment

* Prevention:
  - Install dependencies properly using pip/conda rather than manipulating sys.path
  - Use proper Python packaging conventions (setup.py, etc.) to manage dependencies
  - Document environment setup requirements clearly in setup.md

## Issue: Incorrect test execution path causing import errors

* Issue: When running tests from the project root, import errors occurred because the import structure assumes tests are run from within the NotionAgent directory.

* Resolution:
  - Identified that tests must be run from the NotionAgent directory for imports to resolve correctly
  - Verified that running `pytest tests` from within the NotionAgent directory works correctly

* Prevention:
  - Document the correct command to run tests: `conda activate services && cd Agents/NotionAgent && pytest tests`
  - Consider adding a pytest.ini file to standardize test configuration
  - When creating new tests, maintain consistent import patterns relative to the package structure

## Issue: Failing test for page deletion functionality

* Issue: One test is failing: `test_page_deletion_with_nested_children` in `test_block_cache.py`. The page is not being properly deleted when invalidated.

* Resolution:
  - Identified that this is a functional issue rather than an import/path issue
  - Documentation added noting the need for further investigation

* Prevention:
  - When implementing functionality like cache invalidation, ensure all related objects are properly deleted
  - Add specific tests for edge cases in parent-child relationships
  - Consider reviewing cascade deletion logic in the cache implementation 