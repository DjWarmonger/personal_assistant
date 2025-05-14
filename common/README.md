# tz_common

A utility library for agentic projects.

## Project Structure

```
common/
├── pyproject.toml       # Project configuration
├── setup.py             # Minimal setup.py that defers to pyproject.toml
├── src/                 # Source code directory
│   └── tz_common/       # Main package
│       ├── __init__.py
│       ├── logs.py
│       ├── utils.py
│       └── ...
└── tests/               # Test directory
    ├── __init__.py
    ├── test_imports.py
    └── test_logs.py
```

## Installation

To install the package in development mode:

```bash
cd common
pip install -e .
```

## Usage

```python
from tz_common.logs import log
from tz_common.utils import TZUtils

# Log messages
log.debug("Debug message")
log.user("User message")
log.error("Error message")

# Use utilities
utils = TZUtils()
images = utils.load_images(["image1.jpg", "image2.png"])
``` 