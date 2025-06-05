**Goal**: Create BlockManager class to centralize block processing and decouple NotionClient from direct  cache operations
	
	**Current Issues**:
	- Block processing logic scattered across NotionClient and BlockHolder
	- NotionClient directly calls cache operations
	- UUID-to-index registration happens inconsistently
	
	**Implementation Plan**:
	
	**Phase 1: Extract UUID Collection Logic**
	- Create `extract_all_uuids(message: dict|list) -> List[CustomUUID]` utility method
	- Extract UUID detection logic from `BlockHolder.convert_to_index_id()`
	- Method traverses JSON and collects UUIDs from: `['id', 'next_cursor', 'page_id', 'database_id', 'block_id']`
	- Remove index dependency from UUID extraction logic
	
	**Phase 2: Create BlockManager Class**
	```python
	class BlockManager:
		def __init__(self, index: Index, cache: BlockCache, block_holder: BlockHolder):
			self.index = index
			self.cache = cache  
			self.block_holder = block_holder
	
		def process_and_store_block(self, raw_data: dict, object_type: ObjectType, 
									parent_uuid: Optional[CustomUUID] = None) -> int:
			# Extract UUIDs, add to index, convert to int IDs, store in cache
			pass
	```
	
	**BlockManager Responsibilities**:
	- Extract all UUIDs from raw Notion API responses
	- Add new UUIDs to index (`self.index.add_uuid()`)
	- Create UUID-to-int mapping
	- Use BlockHolder to clean and convert data
	- Store processed data in cache with proper relationships
	- Return main block's integer ID
	
	**Phase 3: Update NotionClient**
    - Add new method `self.block_manager.process_and_store_block()`
	- Replace `self.cache.add_block()` calls inside NotionClient with `self.block_manager.process_and_store_block()`
	- Remove direct `self.block_holder.convert_message()` calls from NotionClient
	- Simplify data processing pipeline in NotionClient methods
	- NotionClient focuses on: API communication, rate limiting, error handling, orchestration
	
- [ ]  Konwersja uuid na int id przed dodaniem do cache
	
	**Goal**: Store cache data with int IDs from the start instead of converting on retrieval
	
	**Current Issues**:
	- UUIDs not consistently added to index during navigation
	- Cache stores UUID strings, converts to int IDs on retrieval
	- Larger cache footprint due to UUID strings vs int IDs
	- Index update moved to BlockHolder but BlockHolder not consistently used
	
	**Current Flow**: 
	`Raw API Data → Clean Data → Store in Cache → Convert UUIDs to int IDs on retrieval`
	
	**New Flow**:
	`Raw API Data → Extract UUIDs → Add to Index → Convert to int IDs → Clean Data → Store in Cache`
	
	**Implementation Steps**:
	
	**Phase 1: Decouple Index from BlockHolder**
	- Remove `self.index` dependency from `BlockHolder.__init__()`
	- Change `convert_to_index_id()` to accept mapping: `convert_to_index_id(message, uuid_to_int_map: Dict[CustomUUID, int])`
	- Method uses provided mapping instead of calling index directly
	
	**Phase 2: Update Cache Interface**
	- Cache continues to store UUIDs internally (they are immutable and important)
	- Int IDs are optimization layer for AI Agent exposure only
	- BlockManager handles UUID-to-int conversion before exposing data to Agent
	- Cache methods like `add_block()` still accept UUID strings internally
	- Parent-child relationships in cache continue using UUIDs
	- `get_children_uuids()` returns UUIDs, BlockManager converts to int IDs when needed
	- Cache remains UUID-based, conversion happens at BlockManager/Agent interface level
	
	**Phase 3: Integration with BlockManager**
	- BlockManager extracts UUIDs first
	- Registers all new UUIDs with index
	- Creates UUID-to-int mapping
	- Converts data to use int IDs before cache storage
