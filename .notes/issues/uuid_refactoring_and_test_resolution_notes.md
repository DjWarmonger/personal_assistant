## UUID Refactoring and Test Resolution

## Issue: Test Environment and Import Errors
*   `ModuleNotFoundError` for `tz_common` and `Agents` occurred frequently.

## Resolution: Test Environment and Import Errors
*   1.  Ensured the `common` package was reinstalled ( `pip install -e ./common`) after changes to `CustomUUID`.
*   2.  Added `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))` to test files (`test_notion_client.py`, `test_utils.py`, `test_block_tree.py`) to allow imports relative to the `NotionAgent` root.
*   3.  Corrected import statements from, e.g., `Agents.NotionAgent.operations.utils` to `operations.utils`.

## Prevention: Test Environment and Import Errors
*   Establish a consistent way to manage `sys.path` for tests, or configure the test runner (e.g., via `pytest.ini` or `pyproject.toml`) to recognize project structure. Reinstall editable local dependencies after changes.

## Issue: Tooling Problems (File Edits/Deletions)
*   The AI agent (myself) struggled at times to correctly apply complex file edits, especially deletions of multiple test methods.

## Resolution: Tooling Problems (File Edits/Deletions)
*   The user manually intervened for one particularly problematic deletion. In other cases, simplifying the edit request or re-reading the file and trying more targeted edits helped.

## Prevention: Tooling Problems (File Edits/Deletions)
*   (for AI development) Improve the AI's ability to understand and apply complex diffs or provide more granular tools for code manipulation (e.g., "delete method X from class Y in file Z"). 