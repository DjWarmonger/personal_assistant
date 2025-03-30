# Architecture and Style Guidelines

## Core Principles

1. **State vs Logic Separation**
   - State objects (like `JsonAgentState`) should be pure data containers
   - No methods in state classes - they should be typed dicts only
   - Logic should reside in tool classes or standalone functions
   - State objects should use `Field` from pydantic for proper typing

2. **Tool Architecture**
   - Tools inherit from `ContextAwareTool`
   - All tool operations must be async (`async def _run`)
   - Tools should handle their own state management
   - Tools should use descriptive names and clear docstrings
   - Return type must be `tuple[AgentState, str]`

3. **Code Organization**
   - Operations (core logic) in separate modules
   - Agent tools in dedicated agent directory
   - Tests mirror the source structure
   - Clear separation between CRUD operations and agent tools

## Style Guidelines

1. **Python Specific**
   - Use tabs for indentation
   - Opening curly bracket only at the beginning of line
   - Follow flake8 formatting
   - Import order:
     1. Python standard library
     2. 3rd party libraries
     3. tz_common imports
     4. Local project files

2. **Type Hints**
   - Always use proper type hints
   - Use pydantic v1 for models
   - Define custom types for clarity (e.g., `JsonDocument = Dict[str, Any]`)

3. **Enums and Constants**
   - Use enums for fixed sets of values. Avoid magic numbers or free-form strings.
   - Document enum values with comments
   - Keep enums close to where they're used

## Testing Guidelines

1. **Async Testing**
   - Use `@pytest.mark.asyncio` decorator for async tests
   - Always await async operations properly
   - Test both success and error cases
   - Test default parameter values

2. **Test Organization**
   - Group related tests together
   - Use descriptive test names
   - Test state through tools, not directly
   - Include edge cases and error conditions

## Common Anti-patterns to Avoid

1. **State Management**
   ❌ Don't add methods to state classes
   ❌ Don't modify state directly, use tools
   ✅ Use typed dicts for state
   ✅ Keep state classes simple

2. **Tool Implementation**
   ❌ Don't mix sync and async code
   ❌ Don't return raw data without context
   ✅ Always use async/await
   ✅ Return both state and result

3. **Code Organization**
   ❌ Don't put logic in state classes
   ❌ Don't mix concerns in single files
   ✅ Separate operations from tools
   ✅ Keep related code together

## Implementation Checklist

When implementing new features:

1. **State Changes**
   - [ ] State classes are pure data containers
   - [ ] Using pydantic Fields for typing
   - [ ] No methods in state classes

2. **Tool Implementation**
   - [ ] Inherits from ContextAwareTool
   - [ ] Implements async _run method
   - [ ] Returns tuple[AgentState, str]
   - [ ] Includes proper type hints

3. **Testing**
   - [ ] Uses pytest.mark.asyncio
   - [ ] Tests through tool interface
   - [ ] Includes error cases
   - [ ] Tests default values

4. **Documentation**
   - [ ] Clear docstrings
   - [ ] Type hints
   - [ ] Example usage where needed

## Project Structure Example

```
Agents/JsonAgent/
├── operations/         # Core logic
│   ├── __init__.py
│   └── json_crud.py
├── Agent/             # Agent-specific code
│   ├── __init__.py
│   ├── agentState.py  # Pure state containers
│   └── agentTools.py  # Tool implementations
├── tests/            # Test mirror structure
│   ├── __init__.py
│   └── test_*.py
└── docs/             # Documentation
    └── *.md
```

## Key Takeaways

1. Keep state and logic separate
2. Use async/await consistently
3. Test through tool interfaces
4. Maintain clear type hints
5. Follow established project structure 