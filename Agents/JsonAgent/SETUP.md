# Setup Instructions

## Running Unit Tests

To run the unit tests for the JsonAgent:

1. First, navigate to the JsonAgent directory:
   ```
   cd Agents/JsonAgent
   ```

2. Activate the conda environment:
   ```
   conda activate services
   ```

3. Run the tests from the JsonAgent directory:
   ```
   python -m pytest -s tests/
   ```

This will run all tests with output streaming enabled. Note that all tests should be run from the JsonAgent directory, not from the project root directory.
