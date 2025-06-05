# Refactoring of block handling

- [✅]  Najpierw wyodrębnienie metod `clean` do osobnej klasy - `BlockHolder`
    - [✅]  Umieścić nową klasę jako składową klienta
- [✅]  Klasa Pydantic o nazwie `BlockDict` (int id -> Block content)
- [✅]  Od teraz klientów Notion będzie zwracał alternatywę str / dict
- [ ]  Umieszczenie bloków w nowej klasie - przeniesienie funkcjonalności zarządzania bloków z klienta Notion
	
- [✅]  Użycie klasy  / `BlockDict` w toolach
- []  Użycie klasy `BlockHolder` w toolach
- [✅]  Użycie klasy `BlockDict` w logice agenta
- []  Użycie klasy `BlockHolder` w logice agenta

## Cache and Filtering Separation (Phase 2)

### Core Architecture Changes

- [✅]  **Separate caching from filtering**: Cache stores full, unfiltered blocks with only UUID→int conversion
    - [✅]  Create `FilteringOptions` enum with categories:
        - `TIMESTAMPS` - remove last_edited_time, created_time
        - `STYLE_ANNOTATIONS` - remove bold, italic, strikethrough, underline, annotations, plain_text
        - `METADATA` - remove icon, cover, archived, in_trash, last_edited_by, created_by
        - `EMPTY_VALUES` - remove null/empty dict/list values
        - `TYPE_FIELDS` - remove type fields
        - `URLS` - remove/convert URL fields
        - `SYSTEM_FIELDS` - remove request_id
        - `MINIMAL` - combination of TIMESTAMPS + STYLE_ANNOTATIONS + METADATA + EMPTY_VALUES
        - `AGENT_OPTIMIZED` - combination of MINIMAL + TYPE_FIELDS + URLS + SYSTEM_FIELDS
    - [✅]  Refactor `BlockHolder` methods:
        - [✅]  Split `convert_message()` into `convert_uuids_to_int()` and `apply_filters()`
        - [✅]  Keep `extract_all_uuids()` as-is (no changes)
        - [✅]  Convert individual clean methods to use filtering options:
            - [✅]  `clean_response_details()` → use METADATA + EMPTY_VALUES + SYSTEM_FIELDS options
            - [✅]  `clean_timestamps()` → use TIMESTAMPS option
            - [✅]  `clean_type()` → use TYPE_FIELDS option
            - [✅]  `convert_urls_to_id()` → use URLS option
        - [✅]  Add new method `apply_filters(data, filter_options: List[FilteringOptions])` 

### BlockManager Updates

- [✅]  **Update caching logic in BlockManager**:
    - [✅]  `process_and_store_block()`: Store data with only UUID conversion, no filtering
    - [✅]  `process_and_store_search_results()`: Store raw results with UUID conversion only
    - [✅]  `process_and_store_database_query_results()`: Store raw results with UUID conversion only
    - [✅]  Add new method `get_filtered_block_content(uuid, filter_options)` for retrieving with dynamic filtering

### Dynamic Filtering on Retrieval

- [✅]  **Update retrieval methods to apply filtering dynamically**:
    - [✅]  Modify `NotionClient` methods to accept filtering options:
        - [✅]  `get_notion_page_details(filter_options=FilteringOptions.AGENT_OPTIMIZED)`
        - [✅]  `get_block_content(filter_options=FilteringOptions.AGENT_OPTIMIZED)`
        - [✅]  `search_notion(filter_options=FilteringOptions.AGENT_OPTIMIZED)`
        - [✅]  `query_database(filter_options=FilteringOptions.AGENT_OPTIMIZED)`
    - [✅]  Apply filtering when retrieving from cache or returning fresh API data
    - [✅]  Ensure agents receive filtered data as before (backward compatibility)

### Tool Integration

- [✅]  **Update agent tools to use filtering**:
    - [✅]  Agent tools should request `FilteringOptions.AGENT_OPTIMIZED` by default
    - [✅]  Some tools may need less aggressive filtering (e.g., `FilteringOptions.MINIMAL`)
    - [✅]  Writer agent tools might need different filtering options than navigation tools

### Filtering Optimization

- [✅]  **Centralized filtering in agentTools.py**:
    - [✅]  Removed `filter_options` parameters from all NotionClient methods
    - [✅]  NotionClient now returns unfiltered data only
    - [✅]  All filtering now happens once in `handle_client_response()` in agentTools.py
    - [✅]  Converted all result types to BlockDict before applying filtering
    - [✅]  Updated tests to reflect new architecture

### Testing and Validation

- [ ]  **Comprehensive testing**:
    - [ ]  Unit tests for new filtering system
    - [ ]  Verify cache stores unfiltered data with UUID conversion
    - [ ]  Verify agents receive properly filtered data
    - [ ]  Performance tests to ensure dynamic filtering doesn't impact performance significantly
    - [ ]  Integration tests for all filtering option combinations

### Migration Strategy

- [ ]  **Gradual migration approach**:
    - [✅]  Phase 1: Implement filtering system alongside existing system
    - [✅]  Phase 2: Update BlockManager to store unfiltered data
    - [✅]  Phase 3: Update NotionClient to use dynamic filtering
    - [✅]  Phase 4: Update agent tools
    		- [✅]  Phase 5: Remove old filtering logic
		- [✅]  Removed legacy methods from `BlockHolder`: `convert_message()`, `clean_response_details()`, `convert_to_index_id()`, `convert_urls_to_id()`, `clean_timestamps()`, `clean_type()`
		- [✅]  Removed legacy method from `BlockManager`: `process_and_store_block_legacy()`, `get_filtered_block_content()`
		- [✅]  Updated method docstrings to remove phase references
		- [✅]  Removed legacy tests and updated remaining tests
		- [✅]  All 77 tests passing
	- [ ]  Phase 6: Clear cache to remove old filtered data


- [ ]  **Aktualizacja testów** → test, powtarzać do skutku
- [ ]  **Refactoring `BlockTree`**, jeśli jest potrzebny?

# FIXME:


## Query database fail - database is cached with block: prefix

This is actually a page and not a database

* Investigate task message passed from Planner to Notion Agent

## Call tool failed

* 1

Call tool failed: Tool 'NotionGetChildren (ICqo3V3hdKzMWHS2OvivvwOx)' failed: Object of type BlockDict is not JSON serializable
Call tool failed: Tool 'NotionGetChildren (Sbk369h10ulmTsXrBd0GPlV0)' failed: Object of type BlockDict is not JSON serializable
Call tool failed: Tool 'NotionGetChildren (5Optk6YOkqBbURb70el6FB7g)' failed: Object of type BlockDict is not JSON serializable
Call tool failed: Tool 'NotionGetChildren (CYOqVjp8mLscehBfsFhhFsIg)' failed: Object of type BlockDict is not JSON serializable

2 *

Calling tool: NotionGetChildren (DiYrgCyrZk9Bk8NW7mLLai8D)
input_args:{'index': '4fa780c8df7746ff83500cd7d504c3d7'}
Retrieving children of Notion block... 4fa780c8df7746ff83500cd7d504c3d7
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 2039efeb6676804c8007f9612d70eb06
Processed and stored block 22
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 1f89efeb6676804ea715ec129630f1d4
Processed and stored block 23
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 1b19efeb6676806082bbe87ca38fc713
Processed and stored block 24
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 2089efeb667680afb111e683c1707d4c
Processed and stored block 25
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 2079efeb66768056bb6bd7f781706fac
Processed and stored block 26
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 2089efeb667680129c88e1cff5b5e3a0
Processed and stored block 27
Updating relationship: 4fa780c8df7746ff83500cd7d504c3d7 -> 2099efeb667680ebac43cd879acfb8c1
Processed and stored block 28
Added parent-children relationships: 4fa780c8df7746ff83500cd7d504c3d7 -> 7 children
Retrieving children recursively for block 4fa780c8df7746ff83500cd7d504c3d7
Call tool failed: Tool 'NotionGetChildren (DiYrgCyrZk9Bk8NW7mLLai8D)' failed: Object of type BlockDict is not JSON serializable

## Notion Agent uses page id as task id for CompleteTask

Notion Agent correctly realizes that page is already added. But then tries to call "CompleteTask" with page id instead of task id,

## Action status message in Agent context is incorrect:

* Action name shouldn't start from "FAILED"
* Task status is 'completed' but it's FAILED
* Resolution is generated by agent, should be empty if action failed

Action taken: FAILED     qbms8hEr3i1TZh0AJgzRdf62 - complete_task (qbms8hEr3i1TZh0AJgzRdf62) with args: {'task_id': '4fa780c8df7746ff83500cd7d504c3d7', 'status': 'completed', 'resolution': "Added TODO page to favourites and displayed today's tasks from...

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
