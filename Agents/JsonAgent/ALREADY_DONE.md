# Json Agent implementation

Implement basic CRUD operations in a JSON document

+ Json document will be provided as an argument to every method ✅

## Basic CRUD implementation

* Store CRUD operations in a separate folder ✅

+ Search path in a JSON document - with a wildcard ✅
    - Return {path : object} ✅
+ Modify object in a JSON document under given path ✅
+ Add object to a JSON document under given path ✅
+ Delete object in a JSON document under given path ✅

## Unit tests in pytest

* Store unit tests in a separate folder ✅

+ Test search path ✅
+ Test modify object ✅
+ Test add object ✅
+ Test delete object ✅

+ Add cmd to run tests to @.vscode/restore-terminals.json ✅

## Agent Tools Implementation

* Create Agent directory with proper structure ✅
* Create agentTools.py with LangChain tools for JSON operations ✅
  - JsonSearchTool ✅
  - JsonModifyTool ✅
  - JsonAddTool ✅
  - JsonDeleteTool ✅
  - JsonLoadTool ✅
  - JsonSaveTool ✅
  - Search via regex key at arbitrary level, case-insinsitive. Return all matches. ✅

- Create method and agent tool that allows agent to get info about current json document ✅
  - Take json path as an argument ✅
  - If path points to object, list all keys of the object. If it's empty, return "EMPTY" ✅
  - If path points to array, return size of the array. If it's empty, return "EMPTY" ✅

## Pretty JSON Summary Feature Documentation
### Overview

We have implemented a human-readable formatting option for JSON summaries in the adaptive_summarize_text function. This feature allows users to toggle between standard machine-parseable output and a more visually structured format designed for human consumption.

### Implementation Details
The enhancement includes:
1. Added a new parameter pretty_output (default: False) to the adaptive_summarize_text function to maintain backward compatibility

2. Created a new helper function format_summary_for_humans that transforms plain text JSON summaries into a more readable format with:

* Hierarchical indentation using tabs instead of spaces
* Bullet points (●) for root-level items
* Tree-like branches (└─) for nested structures
* Proper multi-line output with appropriate spacing

### Usage

```python
# Standard output (machine-readable)
summary, depth = adaptive_summarize_text(data, target_size=1000)

# Human-readable formatted output
pretty_summary, depth = adaptive_summarize_text(data, target_size=1000, pretty_output=True)
```

### Benefits

* Improves readability of complex nested JSON structures
* Maintains original functionality when pretty output is not needed
* Provides clear visual hierarchy through consistent indentation and structural indicators
* Helps users quickly scan and understand the structure of large JSON objects
* Preserves information density while making the format more approachable

The pretty output is especially valuable when presenting JSON summaries in documentation, logs, or user interfaces where human interpretation is the primary goal.


# Agent Logic

## Create main logic loop in LangGraph

* Allow Agent to call any number of tools in loops ✅
* Allow Agent to return response directly to user OR continue operation ✅
* Store list of performed Actions and show it to Agent✅