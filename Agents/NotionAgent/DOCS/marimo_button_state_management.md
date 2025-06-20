### 1. What `mo.state(value)` really returns

`mo.state(initial)` **doesn’t give you a widget-like object**.
It immediately returns **a 2-tuple** →

```python
get_x, set_x = mo.state(0)
```

* `get_x` – a *function* that returns the current value.
* `set_x` – a *function* that overwrites that value (or, if you pass a lambda, mutates it based on the previous value).

That tuple has no `.value`, which is why you hit
`AttributeError: 'tuple' object has no attribute 'value'` ([github.com][1])

---

### 2. Reading & updating state correctly

```python
current = get_x()            # read
set_x(42)                    # overwrite
set_x(lambda v: v + 1)       # mutate
```

No attributes, no “dot access” – just call the two functions.

---

### 3. A canonical button pattern that persists

```python
import marimo as mo

# global state (one cell, executed once)
get_clicks, set_clicks = mo.state(0)

# UI element (second cell)
btn = mo.ui.button(
    label="Click me",
    value=None,                     # we let state hold the count
    on_click=lambda _: set_clicks(lambda v: v + 1)
)
btn

# display (third cell)
mo.md(f"Total clicks: **{get_clicks()}**")
```

* The handler receives the button’s **previous** `value` (here we ignore it) and calls the **setter**.
* Because `get_clicks` is a *global* variable, every cell that references it is re-run automatically after each click, giving you live updates.
* The count lives in the runtime, not in the button, so it survives full-page or timer refreshes.

---

### 4. Making the state visible in other cells

Just **assign the getter to a top-level variable** in its own cell (as above). Any other cell can call `get_clicks()` and will re-execute reactively when the setter fires. You do **not** need to `return` it; the global variable is enough.

---

### 5. Surviving `mo.ui.refresh()` (auto-rerun timers)

`mo.state` objects are held in the notebook’s runtime, **not** in the cell that created them, so they persist as long as the session lives.
To keep them from being recreated on every timer tick:

1. Put the `mo.state(...)` call in a cell that is **outside** the part of the notebook you refresh.
2. In the refresh-driven cells, just *read* the getter.

For simple counters or toggles you can skip `mo.state` entirely and let the **button itself carry the state**:

```python
counter_btn = mo.ui.button(
        label="Click",
        value=0,
        on_click=lambda v: v + 1)
counter_btn.value            # read elsewhere
```

The button keeps its `.value` across refreshes because it is also stored in the runtime ([docs.marimo.io][2])

---

#### Take-away cheat-sheet

| need                                       | minimal code                                  |
| ------------------------------------------ | --------------------------------------------- |
| remember extra data that isn’t in a widget | `get_x, set_x = mo.state(initial)`            |
| read it                                    | `get_x()`                                     |
| change it                                  | `set_x(new)` **or** `set_x(lambda v: …)`      |
| wire to a button                           | `mo.ui.button(on_click=lambda _: set_x(...))` |
| show it                                    | call `get_x()` (cells autorefresh)            |

Use `mo.state` sparingly – most dashboards work fine with the built-in `.value` on UI elements ([docs.marimo.io][3])

[1]: https://github.com/marimo-team/marimo/blob/main/docs/guides/state.md?plain=true&utm_source=chatgpt.com "marimo/docs/guides/state.md at main - GitHub"
[2]: https://docs.marimo.io/api/inputs/button/ "Button - marimo"
[3]: https://docs.marimo.io/guides/state/ "Dangerously set state - marimo"
