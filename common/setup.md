# tz_common Setup

## Environment Requirements

This package must be used with the `services` conda environment:

```bash
conda activate services
```

## Installation

Install the package in development mode:

```bash
cd common
pip install -e .
```

## Dependencies

Some modules have dependencies on local packages:

- `tzrag.py` depends on the LightRAG package, which should be installed from:
  ```bash
  cd F:\AI\LightRAG
  pip install -e .
  ```

## Testing

Run tests with:

```bash
# Activate the correct environment
conda activate services

# Run all tests
cd common
python -m unittest discover

# Run specific test
python -m unittest tests/test_imports.py
```

### Here's what actually worked:

1. Verified Installation: I ensured the tz_common package was correctly installed by checking the site-packages directory.

2. Extracted Egg File: I manually extracted the contents of the `tz_common-0.3-py3.10.egg` file using Python's `zipfile` module. This ensured the package's contents were accessible in the directory `c:/users/tomas/miniconda3/envs/services/lib/site-packages/tz_common`.

3. Adjusted PYTHONPATH: I added the extracted directory to the `PYTHONPATH` to make sure Python could find and import the `tz_common` module when running your script.