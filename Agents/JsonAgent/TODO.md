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
  - Search via regex key at arbitrary level, case-insinsitive. Return all matches.

- Create method and agent tool that allows agent to get info about current json document ✅
  - Take json path as an argument ✅
  - If path points to object, list all keys of the object. If it's empty, return "EMPTY" ✅
  - If path points to array, return size of the array. If it's empty, return "EMPTY" ✅

## Logic

Create main logic loop in LangGraph

* Allow Agent to call any number of tools in loops ✅
* Allow Agent to return response directly to user OR continue operation ✅
* Store list of performed Actions and show it to Agent✅

## Agent implementation

* Agent prompt✅
* Launch as chat✅
* Read response from agent and save it. Use it to continue the chat.

## CLI

* Launch from CLI✅
    - Provide file path as a default argument✅
    - provide separate argument for input and output file paths

# Tests

* Create example usage scenarios


