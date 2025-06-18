# Refactoring of Notion Client

## Clean Up

- [ ] Do not print errors and rethrow them

# Features

## Generate captions for blocks - IMPLEMENTATION PLAN

### Overview
Implement automatic caption generation for blocks whenever they are added or updated. The system should generate short captions (one sentence max, or just a word) using asynchronous calls to a cheap model, update the name in the index table, and run in the background without slowing down the main thread.
Captions are aimed at writing agent, which should receive minmal but sufficient summary of the block.

### Architecture Components

#### 1. Caption Generator Service (`operations/captioning/captionGenerator.py`)
- **Purpose**: Core service responsible for generating captions using OpenAI API
- **Key Methods**:
  - `generate_caption_async(block_content: dict, block_type: str) -> Optional[str]`
  - `_extract_text_content(block_content: dict) -> str` - Extract meaningful text from block. Use BlockHolder class to filter out maningful fields.
  - `_create_caption_prompt(text_content: str, block_type: str) -> str` - Create optimized prompt
- **Features**:
  - Use `send_openai_request` from `tz_common.aitoolbox.AIToolbox`
  - Use cheap model (gpt-4o-mini) with low temperature (0.0)
  - Max tokens: 50 (for short captions)
  - Robust error handling - failures should not interrupt main flow
  - Content filtering - skip blocks with no meaningful text content

#### 2. Background Caption Processor (`operations/captioning/backgroundProcessor.py`)
- **Purpose**: Manages background processing queue and async execution
- **Key Methods**:
  - `queue_caption_generation(uuid: CustomUUID, int_id: int, block_content: dict, block_type: str)`
  - `_process_caption_queue()` - Background worker method
  - `start_background_processing()` / `stop_background_processing()`
- **Features**:
  - Use `asyncio.Queue` for thread-safe task queuing
  - Background `asyncio.Task` for continuous processing
  - Batch processing capability (process multiple captions concurrently)
  - Graceful shutdown handling
  - Rate limiting to avoid API overuse

#### 3. Integration Points

##### A. BlockManager Integration (`operations/blocks/blockManager.py`) - ✅ **COMPLETED**
- **Hook Location**: `process_and_store_block()` method after successful storage
- **Conditional Logic**: ✅ Only queue for blocks that don't already have names in index
- **Testing**: ✅ Added 5 comprehensive test cases covering all scenarios
- **Integration**: ✅ Works for all block processing (main blocks, children, search results)

##### B. CacheOrchestrator Integration (`operations/blocks/cacheOrchestrator.py`) - ✅ **COMPLETED**
- **Hook Locations**: 
  - ✅ `get_or_fetch_page()` - delegates to `BlockManager.process_and_store_block()`
  - ✅ `get_or_fetch_database()` - delegates to `BlockManager.process_and_store_block()`  
  - ✅ `cache_search_results()` - delegates to `BlockManager.process_and_store_search_results()`
  - ✅ `cache_database_query_results()` - delegates to `BlockManager.process_and_store_database_query_results()`
- **Implementation**: ✅ Integration works automatically through BlockManager delegation
- **Testing**: ✅ Added 5 comprehensive integration tests verifying caption generation triggers
- **Architecture**: ✅ No code changes needed - existing delegation pattern provides integration

##### C. Index Integration (`operations/blocks/index.py`) - ✅ **COMPLETED**
- **New Method**: ✅ `update_name_if_empty(int_id: int, name: str) -> bool`
- **Purpose**: ✅ Only update name if current name is empty/default
- **Thread Safety**: ✅ Use existing `db_lock` for safe concurrent access
- **Implementation**: ✅ Method already existed and working correctly
- **Testing**: ✅ Added 12 comprehensive test cases in `test_index.py`
- **Integration**: ✅ Used by BackgroundCaptionProcessor for caption updates

#### 4. Configuration and Dependencies

##### A. NotionService Integration (`operations/notion/notionService.py`)
- **Constructor Update**: Accept optional `caption_processor` parameter
- **Dependency Injection**: Pass processor to BlockManager and CacheOrchestrator

##### B. NotionClient Integration (`operations/notion/notion_client.py`)
- **Initialization**: Create and start BackgroundCaptionProcessor
- **Cleanup**: Ensure proper shutdown in `__aexit__`

##### C. AIToolbox Integration
- **Usage**: Import and use existing `send_openai_request` method
- **Configuration**: Use project's existing OpenAI API key and settings

### Implementation Steps

#### Phase 1: Core Caption Generation
1. Create `CaptionGenerator` class with text extraction and prompt creation
2. Implement `generate_caption_async()` with proper error handling
3. Create unit tests for caption generation logic
4. Test with various block types (paragraph, heading, list, etc.)

#### Phase 2: Background Processing
1. Create `BackgroundCaptionProcessor` with async queue management
2. Implement background worker with proper lifecycle management
3. Add integration hooks to BlockManager
4. Test background processing with mock blocks

#### Phase 3: Integration Points - ✅ **COMPLETED**
1. ✅ **A. BlockManager Integration** - Added conditional caption generation logic
2. ✅ **B. CacheOrchestrator Integration** - Works automatically through BlockManager delegation  
3. ✅ **C. Index Integration** - `update_name_if_empty()` method ready and tested

#### Phase 4: Full Integration - ✅ **COMPLETED**

##### A. NotionService Integration (`operations/notion/notionService.py`) - ✅ **COMPLETED**
- **Constructor Update**: ✅ Accept optional `caption_processor` parameter
- **Dependency Injection**: ✅ Pass processor to BlockManager and store as instance variable
- **Testing**: ✅ Updated test fixtures to handle new optional parameter

##### B. NotionClient Integration (`operations/notion/notion_client.py`) - ✅ **COMPLETED**
- **Initialization**: ✅ Create and start BackgroundCaptionProcessor with proper configuration
- **Constructor Parameters**: ✅ Added `enable_caption_generation=True` and `langfuse_handler=None` parameters
- **Component Wiring**: ✅ Pass caption processor to BlockManager and NotionService
- **Lifecycle Management**: ✅ Start background processing in `__aenter__()` and stop in `__aexit__()`
- **Error Handling**: ✅ Graceful degradation when caption initialization fails
- **Configuration**: ✅ Configurable batch size, queue size, and concurrency limits
- **Testing**: ✅ Created comprehensive integration test suite (`test_caption_integration.py`)
- **Backward Compatibility**: ✅ All existing NotionClient instantiations work without changes
- **Agent Integration**: ✅ Works seamlessly with existing agent tools in `agentTools.py`

##### C. Integration Testing - ✅ **COMPLETED**
- **Full Workflow Tests**: ✅ End-to-end caption generation lifecycle
- **Error Handling Tests**: ✅ Graceful handling of API failures
- **Conditional Logic Tests**: ✅ Skip caption generation for blocks with existing names
- **Concurrent Processing Tests**: ✅ Multiple blocks processed simultaneously
- **Lifecycle Tests**: ✅ Background processing start/stop verification
- **Configuration Tests**: ✅ Enable/disable caption generation functionality

#### Phase 5: Optimization and Monitoring
- Implement rate limiting and batch processing optimizations

### Technical Considerations

#### Error Handling Strategy
- **Non-blocking**: Caption generation failures must never interrupt main block processing
- **Fallback**: Continue without caption if generation fails

#### Performance Considerations
- **Async Processing**: Use `asyncio.gather()` for concurrent caption generation
- **Queue Management**: Limit queue size to prevent memory issues
- **Rate Limiting**: Respect OpenAI API rate limits
- **Caching**: Don't regenerate captions for blocks that already have names

#### Content Filtering
- **Skip Empty Blocks**: Don't generate captions for blocks with no text content
- **Skip System Blocks**: Avoid captioning purely structural blocks
- **Text Extraction**: Focus on meaningful text content (titles, paragraphs, lists)

### Configuration Options
- `ENABLE_CAPTION_GENERATION`: Global enable/disable flag
- `CAPTION_BATCH_SIZE`: Number of captions to process concurrently
- `CAPTION_QUEUE_MAX_SIZE`: Maximum queue size before dropping requests
- `CAPTION_MODEL`: OpenAI model to use (default: gpt-4o-mini)
- `CAPTION_MAX_TOKENS`: Maximum tokens for caption generation (default: 50)

## Generate caption for every block **loaded** from cache, if it doesn't have a name - ✅ **COMPLETED**

### Implementation Summary
- ✅ **CacheOrchestrator Integration**: Added `_queue_caption_for_cached_block()` method
- ✅ **Cache Hit Caption Generation**: Caption generation now triggers when blocks are loaded from cache
- ✅ **Conditional Logic**: Only generates captions for blocks without existing names
- ✅ **Coverage**: Implemented for pages, databases, blocks, and database query results
- ✅ **Testing**: Added comprehensive integration tests for all cache loading scenarios
- ✅ **Property Extraction Fix**: Fixed CaptionGenerator to handle page properties without explicit type fields

### Integration Points
- ✅ `get_or_fetch_page()` - Triggers caption generation on cache hits
- ✅ `get_or_fetch_database()` - Triggers caption generation on cache hits  
- ✅ `get_or_fetch_block()` - Triggers caption generation on cache hits
- ✅ `get_cached_block_content()` - Triggers caption generation when retrieving cached content
- ✅ `get_cached_database_query_results()` - Triggers caption generation for cached query results
- ❌ `get_cached_search_results()` - **Intentionally excluded** (search results are references, not new content)

### Technical Notes
- Caption generation only occurs if the block has no existing name in the index
- Uses the same BackgroundCaptionProcessor for async processing
- Maintains the same conditional logic as storage-time caption generation
- Search results are excluded because they reference existing blocks that may already have captions

# FIXME:

## Weird log at successful attempt to add page to favourites:


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

## Agent does not return any message to user for "add page to favourites"

## index.db is deleted after system restart

Not sure what actually triggers it, but it's not here on a new day

# Optimizations

## Block Filtering Optimizations

## Task optimization

- Make Taks use custom UUID class
- Make Task print shorter format of uuid without dashes

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
