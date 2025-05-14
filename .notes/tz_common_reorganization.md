## tz_common Reorganization and Environment Management

* Issue: tz_common package structure didn't follow Python packaging standards and had problematic imports that caused dependency issues. Tests would fail if dependencies like LightRAG weren't available.

* Resolution: Reorganized `tz_common` using a proper Python packaging structure with `pyproject.toml` and a `src` directory. Added conditional imports for dependencies like `tzrag` which requires the LightRAG library. Updated dependency management to use the `services` conda environment where LightRAG is installed locally.

* Prevention:
  - Use proper Python packaging structure for all new modules with pyproject.toml
  - Always use conditional imports for optional dependencies
  - Document environment requirements (use services conda env)
  - Test both with and without optional dependencies
  - Install local dependencies in development mode when needed
  - Document dependency relationships between components

## Environment-Specific Dependencies

* Issue: LightRAG dependency needed for tzrag is installed in a specific conda environment (services) and is stored in a local repository.

* Resolution: Added conditional import for tzrag in tz_common to allow basic functionality without the dependency. Created comprehensive documentation in Cursor Rules about the environment and dependency requirements.

* Prevention:
  - Always document environment requirements
  - Use conditional imports for environment-specific dependencies
  - Create tests that verify the package works both with and without optional dependencies
  - Clearly specify in documentation which conda environment to use for development and testing 