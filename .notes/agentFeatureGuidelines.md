# Architecture and Style Guidelines

## Implementation Checklist

When implementing new Agent tools and features:

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
