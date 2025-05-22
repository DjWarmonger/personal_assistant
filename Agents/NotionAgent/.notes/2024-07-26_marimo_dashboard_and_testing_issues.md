## Marimo Dashboard and Button Issues

* Issue: Encountered multiple `TypeError` and `RuntimeError` issues when implementing a refresh button and displaying cache metrics in the Marimo dashboard (`Agents/NotionAgent/launcher/dashboard.py`).
    * `TypeError: button.__init__() got multiple values for argument 'on_click'`
    * `AttributeError: 'button' object has no attribute 'on_click'. Did you mean: '_on_click'?`
    * `TypeError: 'str' object is not callable` for `on_click` handler.
    * `RuntimeError: Accessing the value of a UIElement in the cell that created it is not allowed.`
    * Invalid enum value for button `kind` parameter.
* Resolution:
    * Corrected `mo.ui.button` initialization by ensuring `on_click` was handled correctly (or by relying on Marimo's default reactive behavior when a button's value is accessed).
    * Separated UI element (button) creation and its value access into different Marimo cells.
    * Ensured the button's `label` was explicitly used to prevent its text from being mistaken as a callable value.
    * Removed invalid `kind='primary'` from button creation, using the default style.
* Prevention:
    * Clarify Marimo UI element creation and value access patterns: UI elements should be created in one cell, and their `value` should be accessed in a *separate* cell to trigger reactivity or handle events.
    * When using `on_click` or similar event handlers, ensure the correct syntax and that the handler is a callable function, not a string or other non-callable type.
    * Double-check valid parameter values for Marimo UI components (e.g., `kind` for buttons) against the Marimo documentation.

## Incorrect Test Execution

* Issue: Initially attempted to run `pytest` tests without adhering to the project's testing practices (defined in `agents/testing_practices.mdc`), which require activating a specific conda environment.
* Resolution: Corrected the test execution command to include `conda activate services` before running `pytest`.
* Prevention:
    * Always consult project-specific testing guidelines (`agents/testing_practices.mdc`) before running tests.
    * Ensure the correct environment is activated if specified in the testing practices.

## Premature TODO Updates

* Issue: Attempted to update `TODO.md` and `ALREADY_DONE.md` before explicit user confirmation that the feature was working correctly, which violates the `bookkeeping.mdc` guidelines.
* Resolution: Waited for user confirmation before proceeding with documentation updates.
* Prevention:
    * Strictly follow the `bookkeeping.mdc` rule: "After feature is implemented and confirmed to be working, update corresponding TODO, BACKLOG and ALREADY_DONE md files."
    * Always seek explicit user confirmation of feature completion and correctness before modifying task-tracking documents. 