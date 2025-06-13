# Refactoring of Notion Client

## Clean Up

- [ ] Do not print errors and rethrow them

### Success Metrics
- [ ] All existing functionality preserved

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
