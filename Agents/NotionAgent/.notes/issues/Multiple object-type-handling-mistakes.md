# Object Type Handling Mistakes and Misunderstandings

## Assumption That All Notion Objects Are Blocks

* Issue: Initial investigation focused only on block caching, assuming databases would be cached as blocks. Failed to recognize that Notion API has distinct object types (page, database, block) that require different handling.
* Resolution: Implemented object type detection and routing to appropriate cache methods based on `object` field in API responses.
* Prevention: 
  - Always review Notion API documentation for object types before implementing caching
  - Never assume object type - always check the `object` field in responses
  - Design cache architecture to handle multiple object types from the start

## Incomplete Cache Implementation Pattern

* Issue: Implemented cache retrieval (`get_database`) without corresponding cache storage (`add_database` calls), creating asymmetric caching behavior where some objects could be retrieved but never stored.
* Resolution: Added missing `cache.add_database()` and `cache.add_page()` calls in API response handlers.
* Prevention:
  - Follow complete cache patterns: for every `get_*` method, ensure corresponding `add_*` method is called
  - Use checklists when implementing caching: retrieval, storage, invalidation, expiration
  - Add integration tests that verify round-trip caching behavior

## Misunderstanding Notion API Return Types

* Issue: Incorrectly assumed database queries return blocks, when they actually return pages. This led to using wrong invalidation methods and object type handling.
* Resolution: Corrected to use `invalidate_page_if_expired()` for database query results since they return pages.
* Prevention:
  - Study Notion API documentation thoroughly before implementation
  - Create mapping documentation: endpoint → return type → cache method
  - Test with real API responses to verify assumptions about return types

## Overlooking Search Result Heterogeneity

* Issue: Assumed search results would be homogeneous (all blocks), missing that search can return mixed object types (pages, databases, blocks) in a single response.
* Resolution: Added object type detection loop to handle each result based on its actual `object` field value.
* Prevention:
  - Test search functionality with queries that return mixed object types
  - Design search result processing to handle heterogeneous results from the start
  - Never assume API collections contain homogeneous object types

## Inconsistent Method Naming and Missing Implementation

* Issue: Referenced `add_database_query_results()` method that didn't exist, indicating incomplete API design where method names were planned but implementation was missing.
* Resolution: Implemented the missing method with proper parameter handling and type conversion.
* Prevention:
  - Use interface-first design: define all required methods before implementation
  - Implement stub methods early to avoid runtime errors during development

## Hardcoded Constants Reducing Maintainability

* Issue: Used string literals like `"database"` instead of enum values, making code fragile and harder to refactor. This also reduced IDE support for refactoring and error detection.
* Resolution: Replaced all hardcoded strings with `ObjectType.*.value` enum references.
* Prevention:
  - Prefer strongly-typed approaches over string-based comparisons

## Insufficient Test Coverage for Edge Cases

* Issue: Tests focused on happy path scenarios without verifying object type isolation, cache prefix correctness, or cross-type method behavior.
* Resolution: Added tests specifically for database caching prefixes and invalidation method isolation.
* Prevention:
  - Design tests to verify object type boundaries and isolation
  - Test negative cases: ensure wrong methods don't affect wrong object types
  - Add tests for cache key format validation to catch prefix issues early 