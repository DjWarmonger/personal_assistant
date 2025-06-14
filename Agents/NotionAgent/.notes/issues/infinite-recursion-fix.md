# Infinite Recursion in NotionService

## Issue

Tests were freezing at `test_get_block_content_success` with infinite recursion in `NotionService.get_block_content` method. The recursion manifested as:

```
RecursionError: maximum recursion depth exceeded while calling a Python object
```

Stack trace showed circular calls between `get_block_content` → `get_all_children_recursively` → `get_block_children` → `get_block_content`.

## Root Cause

The `get_block_children` method incorrectly called `get_block_content` recursively for each child block:

```python
# WRONG - caused infinite recursion
async def get_child_content_by_int_id(int_id: int) -> tuple[int, dict]:
    child_content = await self.get_block_content(int_id, block_tree=block_tree)
```

This violated the principle that block structures form a tree (directed acyclic graph) where blocks cannot be children of themselves. The recursion was caused by flawed traversal logic, not by the underlying Notion data.

## Resolution

### 1. Added Cycle Detection

Modified `get_all_children_recursively` to track visited nodes:

```python
async def get_all_children_recursively(self, 
                                     block_identifier: Union[str, CustomUUID], 
                                     block_tree: Optional[BlockTree] = None,
                                     visited_nodes: Optional[set] = None) -> BlockDict:
```

Added check: `if parent_uuid_obj in visited_nodes: return BlockDict()`

### 2. Fixed get_block_children Logic

Changed `get_block_children` to only retrieve cached content instead of recursive fetching:

- Added `get_cached_block_content` method to `CacheOrchestrator`
- Modified `get_block_children` to use `self.cache_orchestrator.get_cached_block_content(child_uuid)`
- Removed recursive call to `get_block_content`

### 3. Updated Test Mocks

Fixed test mocks to handle new `visited_nodes` parameter:

```python
async def mock_get_all_children_recursively(block_id, tree, visited_nodes=None):
    return expected_result

# NOTE: The _get_all_children_recursively method has since been completely removed
# and replaced with a queue-based approach in get_block_content
```

## Prevention

- Always respect tree structure assumptions in recursive algorithms
- Add cycle detection to any recursive traversal methods
- Distinguish between "fetch and cache" vs "retrieve cached" operations
- Use descriptive method names that clarify their behavior (`get_cached_block_content` vs `get_block_content`)
- Test recursive methods with proper mocking to catch infinite loops early
- When encountering "maximum recursion depth" errors, investigate the call chain for circular dependencies rather than just increasing recursion limits

## Files Modified

- `Agents/NotionAgent/operations/notionService.py` - Fixed recursion logic
- `Agents/NotionAgent/operations/cacheOrchestrator.py` - Added `get_cached_block_content` method  
- `Agents/NotionAgent/tests/test_notionService.py` - Updated test mocks

## Verification

All 24 tests in `test_notionService.py` now pass, including the previously freezing `test_get_block_content_success`. 