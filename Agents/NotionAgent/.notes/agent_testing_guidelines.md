## Agent Development: Guidelines for Effective Testing

This document provides a set of best practices for creating and maintaining unit and integration tests. Following these guidelines will help avoid common pitfalls such as test redundancy, code duplication, and inefficient workflows.

### 2. Code Quality in Tests

-   **Issue**: High levels of code duplication within test files.
-   **Guideline**: Apply the same code quality standards to test code as to production code. Tests are not second-class citizens; they are critical infrastructure.
    -   **Don't Repeat Yourself (DRY)**: If you find yourself copying and pasting large data structures (e.g., JSON payloads, dictionaries) or setup logic across multiple tests, **stop and refactor**.
-   **Prevention**:
    -   Use **shared constants** or class-level variables for common test data.
    -   Create **helper methods** within the test class to encapsulate complex setup or repeated actions.
    -   For test data that is used across multiple test files, consider creating a dedicated `test_data.py` or a similar shared resource.

### 4. Proactive Refactoring

-   **Issue**: Waiting for user intervention to fix issues like code duplication.
-   **Guideline**: Be proactive in identifying and fixing code smells in tests.
-   **Prevention**: After writing a new test, pause and review it. Ask: "If I were another developer reviewing this code, what would I suggest improving?" Look specifically for duplication and opportunities to improve clarity. Improve the test code *before* presenting it as complete. 