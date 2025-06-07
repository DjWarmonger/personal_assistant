# Langfuse + Pydantic “unhashable type: 'dict'” error

Agent graph → IngestionConsumer

## Symptom
	```bash
	TypeError: unhashable type: 'dict'
	at pydantic\v1\main.py:793 (_get_value)
	```
Repeats for every event Langfuse tries to ingest, right after
event["body"] = event["body"].dict(exclude_none=True).

## Actual root cause

AgentState.unsolvedTasks and completedTasks were set[AgentTask].
When .dict() runs, each AgentTask → plain dict → Pydantic tries
set(converted_items) → fails (dicts are un-hashable).

## Mis-leads / wrong assumptions

### Assumption: A dict is being used as a key somewhere.

Keys were fine; the problem was values turned into dicts inside a set.
 
### Observation: find_bad_keys printed nothing → no issue.

Error appears after Pydantic converts models → dicts, so keys looked OK beforehand.

## Reproduction

```python
from pydantic import BaseModel
class T(BaseModel): id:int
set_of_models = {T(id=1), T(id=2)}
T(id=0, data=set_of_models).dict()   # boom
```

## Diagnostics

```python
# Flags any set that would contain BaseModel instances
from pydantic import BaseModel
def find_sets_with_models(obj, path="root"):
	from collections.abc import Set
	if isinstance(obj, Set) and any(isinstance(x, BaseModel) for x in obj):
		print("set containing BaseModel at", path)
	elif isinstance(obj, dict):
		for k, v in obj.items(): find_sets_with_models(v, f"{path}.{k}")
	elif isinstance(obj, (list, tuple, set)):
		for i, item in enumerate(obj): find_sets_with_models(item, f"{path}[{i}]")
```

## Solution

Replace set inside AgentState with list.

