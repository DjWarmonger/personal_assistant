# COMPREHENSIVE NOTION CLIENT REFACTORING PLAN

## Overview
The current `NotionClient` class (625 lines) has grown too large and handles multiple responsibilities. This plan outlines a comprehensive refactoring to improve maintainability, testability, and follow Single Responsibility Principle.

## Current Issues Analysis

### Responsibility Overload
Current `NotionClient` handles:
- ✗ HTTP API communication with Notion
- ✗ Caching logic (cache checks, invalidation, TTL)
- ✗ Data processing (UUID extraction, conversion, filtering)
- ✗ Business logic (recursive fetching, parent-child relationships)
- ✗ Error handling and response processing
- ✗ Rate limiting coordination
- ✗ Filter parsing and validation
- ✗ Block tree management

### Code Quality Issues
- 625 lines in single class (should be <200)
- Multiple concerns mixed together
- Difficult to unit test individual components
- High coupling between HTTP, cache, and business logic
- Repetitive patterns across similar methods

## Refactoring Strategy

### Phase 1: Extract Pure HTTP Layer
**Goal**: Separate HTTP communication from business logic

**Create**: `NotionAPIClient` class
- **Responsibility**: Raw HTTP calls to Notion API only
- **No dependencies** on cache, index, or business logic
- **Methods**:
  ```python
  async def get_page_raw(self, page_id: str) -> dict
  async def get_database_raw(self, database_id: str) -> dict
  async def get_block_children_raw(self, block_id: str, start_cursor: str = None) -> dict
  async def search_raw(self, query: str, filter_type: str = None, start_cursor: str = None) -> dict
  async def query_database_raw(self, database_id: str, filter_obj: dict = None, start_cursor: str = None) -> dict
  ```
- **Features**:
  - Rate limiting coordination with `AsyncClientManager`
  - Basic error handling (HTTP status codes)
  - Request/response serialization
  - Authentication headers management

### Phase 2: Extract Cache Orchestration
**Goal**: Centralize all cache-related operations

**Create**: `CacheOrchestrator` class
- **Responsibility**: Cache operations, invalidation logic, TTL management
- **Methods**:
  ```python
  async def get_or_fetch_page(self, page_id: CustomUUID, fetcher_func: Callable) -> Optional[str]
  async def get_or_fetch_block(self, block_id: CustomUUID, fetcher_func: Callable) -> Optional[str]
  def invalidate_if_expired(self, uuid: CustomUUID, last_edited_time: str, object_type: ObjectType) -> bool
  def get_cached_search_results(self, query: str, filter_str: str, start_cursor: CustomUUID) -> Optional[str]
  def cache_search_results(self, query: str, results: dict, filter_str: str, start_cursor: CustomUUID, ttl: int)
  ```
- **Features**:
  - Generic cache-or-fetch pattern
  - Centralized invalidation logic for all object types
  - Cache metrics integration
  - TTL management

### Phase 3: Extract Business Logic Service
**Goal**: High-level operations orchestration

**Create**: `NotionService` class
- **Responsibility**: Coordinate between API, cache, and data processing
- **Methods**:
  ```python
  async def get_page_details(self, page_id: Union[str, CustomUUID], database_id: Union[str, CustomUUID] = None) -> Union[BlockDict, str]
  async def get_block_content(self, block_id: Union[str, CustomUUID], get_children: bool, start_cursor: CustomUUID = None, block_tree: BlockTree = None) -> Union[BlockDict, str]
  async def get_children_recursively(self, block_id: Union[str, CustomUUID], block_tree: BlockTree) -> Union[BlockDict, str]
  async def search_notion(self, query: str, filter_type: str = None, start_cursor: CustomUUID = None) -> Union[BlockDict, str]
  async def query_database(self, database_id: Union[str, CustomUUID], filter_obj: dict = None, start_cursor: CustomUUID = None) -> Union[BlockDict, str]
  ```
- **Features**:
  - Orchestrates API calls, caching, and data processing
  - Handles business logic like recursive fetching
  - Manages BlockTree relationships
  - Error propagation and formatting

### Phase 4: Extract Utility Classes
**Goal**: Move specialized utilities to dedicated classes

**Create utilities**:
1. **`FilterParser`**:
   ```python
   class FilterParser:
       @staticmethod
       def parse_filter(filter_input: Union[dict, str, None]) -> dict
       @staticmethod
       def validate_database_filter(filter_obj: dict) -> bool
   ```

- Move parse_filter() method to this class
- Move Filterparser ro utils.py

2. **`ErrorHandler`**:
   ```python
   class ErrorHandler:
       @staticmethod
       def format_http_error(status_code: int, response_data: dict) -> str
       @staticmethod
       def clean_error_message(response_data: dict) -> dict
   ```

3. **`ResponseProcessor`**:
   ```python
   class ResponseProcessor:
       @staticmethod
       def wrap_in_block_dict(data: dict, main_id: int) -> BlockDict
       @staticmethod
       def process_search_results_to_block_dict(results: dict) -> BlockDict
   ```

### Phase 5: Simplify NotionClient
**Goal**: Transform NotionClient into a clean facade

**New `NotionClient`** (~100-150 lines):
```python
class NotionClient:
    def __init__(self, notion_token: str, landing_page_id: str, load_from_disk: bool = True, run_on_start: bool = True):
        # Initialize components
        self.api_client = NotionAPIClient(notion_token)
        self.index = Index(load_from_disk, run_on_start)
        self.cache = BlockCache(load_from_disk, run_on_start)
        self.url_index = UrlIndex()
        self.block_holder = BlockHolder(self.url_index)
        self.block_manager = BlockManager(self.index, self.cache, self.block_holder)
        self.cache_orchestrator = CacheOrchestrator(self.cache, self.block_manager)
        self.service = NotionService(self.api_client, self.cache_orchestrator, self.block_manager, self.index)
        self.landing_page_id = CustomUUID.from_string(landing_page_id) if landing_page_id else None
    
    # Facade methods - delegate to service layer
    async def get_notion_page_details(self, page_id=None, database_id=None) -> Union[BlockDict, str]:
        return await self.service.get_page_details(page_id or self.landing_page_id, database_id)
    
    async def get_block_content(self, block_id, get_children=False, start_cursor=None, block_tree=None) -> Union[BlockDict, str]:
        return await self.service.get_block_content(block_id, get_children, start_cursor, block_tree)
    
    # ... other facade methods
```

## Implementation Plan

### Step 1: Create NotionAPIClient
- [x] Create `notionAPIClient.py` with raw HTTP methods
- [x] Move HTTP-related code from `NotionClient`
- [x] Update tests to mock `NotionAPIClient` instead of HTTP calls
- [x] Ensure rate limiting still works correctly

### Step 2: Create CacheOrchestrator
- [x] Create `cacheOrchestrator.py` 
- [x] Move cache invalidation logic from `NotionClient`
- [x] Implement generic cache-or-fetch pattern
- [x] Update cache-related tests
- [x] **DESIGN ISSUE IDENTIFIED**: CacheOrchestrator uses placeholder ID 0 for all cached items
- [x] **FIX COMPLETED**: Added Index dependency to CacheOrchestrator for proper UUID-to-integer conversion

### Step 2.1: Fix CacheOrchestrator Design Issue
**Problem**: CacheOrchestrator returns placeholder ID `0` for all cached items, breaking BlockDict contracts and creating inconsistent IDs between cache hits/misses.

**Root Cause**: CacheOrchestrator was designed to be independent of Index, but BlockDict requires meaningful integer IDs from Index's UUID-to-integer mapping.

**Solution**: Add Index dependency to CacheOrchestrator for proper UUID-to-integer conversion.

**Benefits**:
- ✅ Consistent IDs between cache hits and cache misses  
- ✅ Proper BlockDict contracts with unique integer IDs
- ✅ Architectural coherence - CacheOrchestrator can fulfill BlockDict requirements
- ✅ No breaking changes to public API

**Implementation Tasks**:
- [x] Add Index parameter to CacheOrchestrator constructor
- [x] Replace placeholder ID `0` with proper `Index.to_int()` calls in:
  - [x] `get_or_fetch_page()` method (line 44)
  - [x] `get_or_fetch_database()` method (line 94) 
  - [x] `get_or_fetch_block()` method (line 134)
- [x] Update CacheOrchestrator tests to provide Index dependency
- [x] Add error handling for failed UUID-to-int conversions
- [x] Verify all tests pass with proper integer IDs

### Step 3: Create Utility Classes
- [x] Create `filterParser.py`, `errorHandler.py`, `responseProcessor.py`
- [x] Move `parse_filter()` method to `FilterParser`
- [x] Move error handling logic to `ErrorHandler`
- [x] Create utility tests

**Step 3 Summary**: Created three utility classes in `operations/utilities/`:
- **FilterParser**: Extracted `parse_filter()` method from NotionClient with validation
- **ErrorHandler**: Centralized error handling and formatting (removed unnecessary `is_retryable_error`)
- **ResponseProcessor**: Utilities for converting API responses to BlockDict format
- **Tests**: 41 comprehensive tests covering all utility functionality

### Step 4: Create NotionService
- [x] Create `notionService.py` with business logic
- [x] Move high-level orchestration from `NotionClient`
- [x] Implement service-level methods

### Step 5: Refactor NotionClient
- [x] Transform `NotionClient` into facade pattern
- [x] Remove moved code and delegate to service layer
- [x] Update all existing references to maintain API compatibility
- [x] Ensure all tests still pass

### Step 6: Clean Up
- [ ] Remove duplicate code and unused imports
- [ ] Add comprehensive documentation
- [ ] Verify success metrics
- [ ] Do not print errors and rethrow them

## Expected Benefits

### Code Quality
- **Single Responsibility**: Each class has one clear purpose
- **Testability**: Easy to unit test individual components
- **Maintainability**: Changes isolated to appropriate classes
- **Readability**: Smaller, focused classes easier to understand

### Architecture
- **Loose Coupling**: Clear interfaces between layers
- **Dependency Injection**: Better separation for testing/mocking
- **Reusability**: HTTP client and utilities can be used elsewhere
- **Extensibility**: Easy to add new features or modify existing ones

### Performance
- **Better Caching**: Centralized cache logic for optimization
- **Debugging**: Clearer responsibility boundaries for troubleshooting

## Compatibility Notes
- [ ] Maintain public API of `NotionClient` for existing `agentTools.py`
- [ ] Keep existing method signatures unchanged
- [ ] Ensure all tests pass without modification
- [ ] No breaking changes for existing consumers

## Testing Strategy
- [ ] Unit tests for each new class
- [ ] Integration tests for the full flow
- [ ] Performance tests comparing old vs new architecture
- [ ] Mock tests for HTTP layer separation
- [ ] Cache behavior verification tests

## File Structure After Refactoring
```
operations/
├── notion_client.py          # Facade class
├── notionAPIClient.py        # HTTP layer
├── cacheOrchestrator.py      # Cache management
├── notionService.py          # Business logic 
├── utilities/
│   ├── filterParser.py       # Filter utilities
│   ├── errorHandler.py       # Error handling
│   └── responseProcessor.py  # Response utilities
└── [existing files unchanged]
```

## Current Status
- Step 1 (NotionAPIClient): ✅ Complete
- Step 2 (CacheOrchestrator): ✅ Complete (design issue fixed)
- Step 2.1 (Fix CacheOrchestrator Design Issue): ✅ Complete
- Step 3 (Create Utility Classes): ✅ Complete
- Next: Step 4 (Create NotionService)

## Success Metrics
- [ ] `NotionClient` reduced from 625 to ~150 lines
- [ ] Each new class under 300 lines
- [ ] 100% test coverage maintained
- [ ] No performance degradation
- [ ] All existing functionality preserved

---

# FIXME:

## Now, no children are returned for TODO list

```
Calling tool: NotionGetBlockContent (ETm4VAU9tIvzjj64UXbPMjcB)
input_args:{'index': '4fa780c8df7746ff83500cd7d504c3d7'}
Retrieving content of Notion block... 4fa780c8df7746ff83500cd7d504c3d7
Result of tool NotionGetBlockContent (ETm4VAU9tIvzjj64UXbPMjcB): SUCCESS{}
```

However, blockTree log iscorrect:

```
Visited blocks for writer:
1
   6
   4
   8
   3
   7
   11
   5
   9
   10
   12
```


## Wrtiter received only one block for TODO list

All visited blocks (id : content):
```json
2 : {'object': 'list', 'results': [{'object': 'block', 'id': 1, 'parent': {'page_id': 22}, 'has_children': False, 'child_database': {'title': 'Agent Notion - Zadania'}}, {'object': 'block', 'id': 42, 'parent': {'page_id': 22}, 'has_children': False, 'bookmark': {'caption': [{'text': {'content': 'Moja integracja'}}]}}, {'object': 'block', 'id': 43, 'parent': {'page_id': 22}, 'has_children': True, 'heading_3': {'rich_text': [{'text': {'content': 'Zalety'}}], 'is_toggleable': True, 'color': 'default'}}, {'object': 'block', 'id': 44, 'parent': {'page_id': 22}, 'has_children': True, 'heading_3': {'rich_text': [{'text': {'content': 'Scenariusze użycia'}}], 'is_toggleable': True, 'color': 'default'}}, {'object': 'block', 'id': 45, 'parent': {'page_id': 22}, 'has_children': True, 'heading_3': {'rich_text': [{'text': {'content': 'Dedykowany agent samodzielnie przeglądający Notion'}}], 'is_toggleable': True, 'color': 'default'}}, {'object': 'block', 'id': 46, 'parent': {'page_id': 22}, 'has_children': True, 'heading_3': {'rich_text': [{'text': {'content': 'Integracja z YouTube'}}], 'is_toggleable': True, 'color': 'default'}}, {'object': 'block', 'id': 47, 'parent': {'page_id': 22}, 'has_children': False, 'paragraph': {'color': 'default'}}, {'object': 'block', 'id': 48, 'parent': {'page_id': 22}, 'has_children': False, 'paragraph': {'color': 'default'}}, {'object': 'block', 'id': 49, 'parent': {'page_id': 22}, 'has_children': False, 'paragraph': {'color': 'default'}}], 'has_more': False}`
```

* All nested blocks are returned as a part of single list. Instyead, these shoudl be nested blocks.

## TODO list was not explored recursively - shoudl be automatic

> All visited blocks (id : content):
```json
1 : {'object': 'page', 'id': 1, 'parent': {'workspace': True}, 'properties': {'title': {'id': 'title', 'title': [{'text': {'content': 'TODO dziś'}}]}}}
2 : {'object': 'list', 'results': [{'object': 'block', 'id': 3, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Agent Notion'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 4, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Patryk Kostek'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 5, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Obiad u mamy'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 6, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Trening w domu'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 7, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Zaplanować zadania na kolejny dzień'}}], 'checked': False, 'color': 'default'}}], 'has_more': False}
3 : {'object': 'block', 'id': 3, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Agent Notion'}}], 'checked': False, 'color': 'default'}}
4 : {'object': 'block', 'id': 4, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Patryk Kostek'}}], 'checked': False, 'color': 'default'}}
5 : {'object': 'block', 'id': 5, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Obiad u mamy'}}], 'checked': False, 'color': 'default'}}
6 : {'object': 'block', 'id': 6, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Trening w domu'}}], 'checked': False, 'color': 'default'}}
7 : {'object': 'block', 'id': 7, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Zaplanować zadania na kolejny dzień'}}], 'checked': False, 'color': 'default'}}
```

```
Tree of blocks visited:
1:TODO dziś
   ├──7
   ├──3
   ├──4
   ├──5
   └──6
```

* Second attempt - only main block was returned, no nested blocks at all

All visited blocks (id : content):
```json
2 : {'object': 'list', 'results': [{'object': 'block', 'id': 3, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Agent Notion'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 4, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Patryk Kostek'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 5, 'parent': {'page_id': 1}, 'has_children': True, 'to_do': {'rich_text': [{'text': {'content': 'Obiad u mamy'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 6, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Trening w domu'}}], 'checked': False, 'color': 'default'}}, {'object': 'block', 'id': 7, 'parent': {'page_id': 1}, 'has_children': False, 'to_do': {'rich_text': [{'text': {'content': 'Zaplanować zadania na kolejny dzień'}}], 'checked': False, 'color': 'default'}}], 'has_more': False}
```

```
Tree of blocks visited:
1:TODO dziś
```

## Query database fail - database is cached with block: prefix

This is actually a page and not a database

* Investigate task message passed from Planner to Notion Agent

## Notion Agent uses page id as task id for CompleteTask

Notion Agent correctly realizes that page is already added. But then tries to call "CompleteTask" with page id instead of task id,

## Block tree is scrambled

Tree of blocks visited:
6
│  ├──31
│  │  └──179
│  ├──27
│  ├──32
│  │  ├──184
│  │  ├──183
│  │  ├──185
│  │  └──186
│  ├──28
│  ├──26
│  ├──33
│  ├──29
│  ├──25
│  ├──30
│  ├──36
│  │  └──180
│  ├──40
│  │  └──182
│  ├──37
│  ├──38
│  │  └──187
│  ├──34
│  ├──35
│  │  └──181
│  └──39
5
│  ├──13
│  ├──15
│  ├──16
│  └──14
4
│  ├──18
│  ├──19
│  ├──20
│  ├──17
│  ├──23
│  ├──22
│  ├──21
│  └──24
1:Integracja z Notion
7
   ├──9
   ├──12
   └──11

* Probably 1 is not recognized as root with children 4, 5, 6, 7

## Action status message in Agent context is incorrect:

* Action name shouldn't start from "FAILED"
* Task status is 'completed' but it's FAILED
* Resolution is generated by agent, should be empty if action failed

Action taken: FAILED     qbms8hEr3i1TZh0AJgzRdf62 - complete_task (qbms8hEr3i1TZh0AJgzRdf62) with args: {'task_id': '4fa780c8df7746ff83500cd7d504c3d7', 'status': 'completed', 'resolution': "Added TODO page to favourites and displayed today's tasks from...



## Weird log at successfdul attempt to add page to favourites:


2025-06-08 08:32:23,817 - DEBUG      - Added to favourites : 123e4567e89b12d3a456426614174000
2025-06-08 08:32:23,817 - DEBUG      - Removed from favourites : 123e4567e89b12d3a456426614174000
2025-06-08 08:32:23,817 - COMMON     - Favourites:[]
2025-06-08 08:32:24,329 - DEBUG      - Processed and stored page 1
2025-06-08 08:32:24,718 - DEBUG      - Processed and stored database 1
2025-06-08 08:32:25,067 - ERROR      - 404
2025-06-08 08:32:34,629 - ERROR      - Identifier 'invalid-uuid' is not a valid URL, UUID, or integer ID.
2025-06-08 08:32:34,629 - ERROR      - Could not convert invalid-uuid to CustomUUID in get_block_children
2025-06-08 08:32:34,636 - ERROR      - Identifier 'invalid-uuid' is not a valid URL, UUID, or integer ID.
2025-06-08 08:32:34,636 - ERROR      - Could not convert invalid-uuid to CustomUUID in get_all_children_recursively
2025-06-08 08:32:35,238 - ERROR      - 404

# Disable cache save during tests

# Optimizations

## Block Filtering Optimizations

- [ ]  **Performance optimizations**:
    - [ ]  Cache filtered versions for frequently requested filter combinations
    - [ ]  Implement lazy filtering for large block trees
    - [ ]  Add metrics for filtering performance

## Task optimization

- Make Taks use custom UUID class
- Make Task print shorter format of uuid without dashes

```
Unsolved tasks:Task Id: b341b0b2-03e3-4491-b2fc-4a05a0fbc501 - Wyświetl wszystkie zadania z dzisiejszej listy TODO na stronie o UUID 4fa780c8df7746ff83500cd7d504c3d7
```

# Misc features

# Extra agent tools

## Tool that shows X favourite pages

- Do not give it to Agent yet
- Allow paging?
- Create unit tests

## Limit number of loop iteration for Agent

- Start with Notion Agent
- Add iteration count to context, as last message
- Mention it in system prompt?

# Marimo dashboard

## Add static field that shows cache hit ratio

## Open logs from multiple tasks ran in parallel in separate tabs

- Make sure text doesn't go out of tab header

## Fix task browser label so it can hold long text (currently it doesn't fit and extends beyond boundaries)

## Create new task in Marimo

- Get all tasks from actual database: https://www.notion.so/11d9efeb667680ed98cffaef689b9cf1?v=65ea497489ca4dd4a58998f5b1242988
