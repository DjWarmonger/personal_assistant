## UUID Refactoring and Test Resolution

## Issue: Initial Goal - Replace String UUIDs with `CustomUUID` Class
*   The primary objective was to replace all string-based UUIDs in the `NotionAgent` project with a new `CustomUUID` class (from `common/src/tz_common/uuid.py`) to improve type safety and consistency. This involved removing an old `UUIDConverter` class.

## Issue: Pydantic Deserialization for `CustomUUID` in `BlockTree`
*   The `BlockTree.from_dict()` method initially performed manual string-to-`CustomUUID` conversion. This led to an `AssertionError` in `test_serialization_round_trip` because Pydantic V1 models, when used as types for dictionary keys or values within another Pydantic model, require a special mechanism to be correctly parsed from strings.

## Resolution: Pydantic Deserialization for `CustomUUID` in `BlockTree`
*   1.  Added `__get_validators__` and a corresponding `validate_custom_uuid_for_pydantic` class method to `CustomUUID`. This allows Pydantic to use `CustomUUID.from_string` automatically when parsing dictionary data into a `BlockTree` model.
*   2.  Simplified `BlockTree.from_dict()` to directly use Pydantic's `cls(**data)` for deserialization, leveraging the new validator in `CustomUUID`.

## Prevention: Pydantic Deserialization for `CustomUUID` in `BlockTree`
*   When using custom types as dictionary keys/values or nested models in Pydantic V1, ensure the custom type implements `__get_validators__` for seamless parsing.

## Issue: Test Failures due to `CustomUUID` Type Expectations
*   Many tests failed because methods updated to expect `CustomUUID` objects were still being passed raw strings, or `CustomUUID.from_string` was called with already converted `CustomUUID` objects or incorrect types (like integers).

## Resolution: Test Failures due to `CustomUUID` Type Expectations
*   1.  Updated test data (e.g., in `test_block_cache.py`, `test_block_tree.py`) to use valid UUID strings that `CustomUUID.from_string` could process.
*   2.  Modified `CustomUUID.from_string` to return the input directly if it's already a `CustomUUID` instance.
*   3.  Ensured that calling code (e.g., `notion_client.py`) correctly passed string UUIDs from API responses to `CustomUUID.from_string` before any other conversions.

## Prevention: Test Failures due to `CustomUUID` Type Expectations
*   When refactoring types, meticulously check all call sites, including test files, to ensure correct type instantiation and argument passing. Make validator/parser methods robust to receiving already-correct types.

## Issue: Test Environment and Import Errors
*   `ModuleNotFoundError` for `tz_common` and `Agents` occurred frequently.

## Resolution: Test Environment and Import Errors
*   1.  Ensured the `common` package was reinstalled ( `pip install -e ./common`) after changes to `CustomUUID`.
*   2.  Added `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))` to test files (`test_notion_client.py`, `test_utils.py`, `test_block_tree.py`) to allow imports relative to the `NotionAgent` root.
*   3.  Corrected import statements from, e.g., `Agents.NotionAgent.operations.utils` to `operations.utils`.

## Prevention: Test Environment and Import Errors
*   Establish a consistent way to manage `sys.path` for tests, or configure the test runner (e.g., via `pytest.ini` or `pyproject.toml`) to recognize project structure. Reinstall editable local dependencies after changes.

## Issue: `BlockCache` `test_batch_deletion` Flakiness/Assertion
*   The `test_batch_deletion` in `test_block_cache.py` was failing an assertion related to block invalidation. This was due to the timestamp used for invalidation being potentially the same as the insertion timestamp.

## Resolution: `BlockCache` `test_batch_deletion` Flakiness/Assertion
*   Added a `time.sleep(0.01)` before the invalidation call to ensure a difference in timestamps. Also added assertions to verify that non-invalidated blocks remained.

## Prevention: `BlockCache` `test_batch_deletion` Flakiness/Assertion
*   When testing time-sensitive logic (like expirations), ensure a clear and reliable difference between timestamps used for setting up state and triggering events.

## Issue: Obsolete/Placeholder Tests in `test_block_tree.py`
*   The file `test_block_tree.py` contained many placeholder tests with `@patch` decorators but no actual assertions relevant to the current `BlockTree` API.

## Resolution: Obsolete/Placeholder Tests in `test_block_tree.py`
*   These tests were removed, and new, relevant tests were added for `is_empty`, `get_tree_str` on an empty tree, duplicate relationships, and `from_dict` with empty inputs.

## Prevention: Obsolete/Placeholder Tests in `test_block_tree.py`
*   Regularly review and clean up test suites to remove obsolete tests that no longer reflect the current codebase, improving clarity and maintainability.

## Issue: Tooling Problems (File Edits/Deletions)
*   The AI agent (myself) struggled at times to correctly apply complex file edits, especially deletions of multiple test methods.

## Resolution: Tooling Problems (File Edits/Deletions)
*   The user manually intervened for one particularly problematic deletion. In other cases, simplifying the edit request or re-reading the file and trying more targeted edits helped.

## Prevention: Tooling Problems (File Edits/Deletions)
*   (for AI development) Improve the AI's ability to understand and apply complex diffs or provide more granular tools for code manipulation (e.g., "delete method X from class Y in file Z"). 