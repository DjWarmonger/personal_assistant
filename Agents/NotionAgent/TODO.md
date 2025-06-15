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

##### A. BlockManager Integration (`operations/blocks/blockManager.py`)
- **Hook Location**: `process_and_store_block()` method after successful storage
- **Implementation**:
  ```python
  # After storing block in cache
  if self.caption_processor:
      self.caption_processor.queue_caption_generation(
          main_uuid, main_int_id, processed_data, object_type.value
      )
  ```
- **Conditional Logic**: Only queue for blocks that don't already have names in index

##### B. CacheOrchestrator Integration (`operations/blocks/cacheOrchestrator.py`)
- **Hook Locations**: 
  - `get_or_fetch_page()` - for new pages
  - `get_or_fetch_database()` - for new databases  
  - `cache_search_results()` - for new search result items
- **Implementation**: Similar queuing pattern as BlockManager

##### C. Index Integration (`operations/blocks/index.py`)
- **New Method**: `update_name_if_empty(int_id: int, name: str) -> bool`
- **Purpose**: Only update name if current name is empty/default
- **Thread Safety**: Use existing `db_lock` for safe concurrent access

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

#### Phase 3: Index Integration
1. Add `update_name_if_empty()` method to Index class
2. Integrate caption updates with background processor
3. Add database migration if needed for caption metadata
4. Test concurrent access and thread safety

#### Phase 4: Full Integration
1. Wire up all components in NotionService and NotionClient
2. Add configuration options for enabling/disabling captioning
3. Implement graceful degradation when captioning fails
4. Add comprehensive integration tests

#### Phase 5: Optimization and Monitoring
1. Add metrics for caption generation success/failure rates
2. Implement rate limiting and batch processing optimizations
3. Add logging for monitoring caption generation performance
4. Fine-tune prompts based on real-world usage

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

#### Testing Strategy
- **Unit Tests**: Test caption generation logic with mock API responses

### Configuration Options
- `ENABLE_CAPTION_GENERATION`: Global enable/disable flag
- `CAPTION_BATCH_SIZE`: Number of captions to process concurrently
- `CAPTION_QUEUE_MAX_SIZE`: Maximum queue size before dropping requests
- `CAPTION_MODEL`: OpenAI model to use (default: gpt-4o-mini)
- `CAPTION_MAX_TOKENS`: Maximum tokens for caption generation (default: 50)

## Unify AIToolbox with Langfuse Handler

- [x] **Integrate AIToolbox with existing langfuse_handler**: Modified AIToolbox to accept an optional `langfuse_handler` parameter in its constructor. When provided, AIToolbox uses the handler's session_id and user_id for consistent tracking. Updated CaptionGenerator to accept and pass the shared langfuse_handler to AIToolbox.

**Integration Example:**
```python
# In Agent/graph.py - existing langfuse_handler
langfuse_handler = create_langfuse_handler(user_id="Notion Agent")

# In NotionClient or wherever CaptionGenerator is instantiated
caption_generator = CaptionGenerator(
    block_holder=self.block_holder,
    langfuse_handler=langfuse_handler  # Pass shared handler
)
```

**Key Changes:**
- AIToolbox constructor now accepts `langfuse_handler: Optional[CallbackHandler] = None`
- When langfuse_handler is provided, AIToolbox uses its session_id and user_id
- CaptionGenerator creates AIToolbox with shared handler: `AIToolbox(user_id="Notion Agent Caption Generator", langfuse_handler=langfuse_handler)`
- All caption generation API calls are now tracked under the same Notion Agent session

- [x] **Update caption generation to use unified tracking**: Caption generation now uses the shared langfuse_handler when provided, ensuring all API calls are tracked alongside other agent operations.

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
