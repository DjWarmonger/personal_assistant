# Migration Plan: Move Notion Agent & `tz_common` from Conda "services" env to `uv`

> Location: `Agents/NotionAgent/TASKS/uv-migration-plan.md`

---

## 0. Objectives
1. Reproduce the **current** Conda environment _exactly_ for rollback.
2. Create a **parallel** `uv`-managed virtual environment (`.venv_uv_services`)
3. Make **no changes** to production CI/CD scripts until the `uv` build passes all tests.
4. Minimise risk by migrating **Notion Agent** first, then extending to any other services that depend on `tz_common`.

---

## 1. Snapshot & Rollback Safety
1. Activate the existing Conda env (`conda activate services`).
2. Freeze exact package versions:
	```bash
	pip list --format freeze > Agents/NotionAgent/TASKS/conda-services-freeze.txt
	conda list --explicit > Agents/NotionAgent/TASKS/conda-services-explicit.txt
	```
4. (Optional) Export Conda env YAML:
	```bash
	conda env export > Agents/NotionAgent/TASKS/conda-services-env.yml
	```

Rollback = `conda activate services` **+** `git checkout notion_uv_migration_start`.

---

## 2. Prepare `uv` Environment ✅ DONE
1. Install `uv` once globally (if not already):
	```bash
	pipx install uv   # or "pip install uv --user"
	```
2. From project root (`PersonalAssistant/`):
	```bash
	uv venv .venv_uv_services
	```
3. Activate:
	```bash
	source .venv_uv_services/bin/activate   # or "./.venv_uv_services/Scripts/activate" on Windows
	```
4. Pin Python version identical to Conda env (e.g. 3.11.x) in a **tool-agnostic** file:
	```
	# .python-version (used by pyenv/direnv, ignored by Conda)
	3.11.6
	```

---

## 3. Dependency Specification ✅ DONE
### 3.1 Convert Conda lockfile → requirements
1. Use `conda-lock` **or** manual script to translate `conda-services-explicit.txt` into `requirements-conda.txt` (pip style).
2. Manually prune any Conda-only libs (`conda`, `anaconda-client`, etc.).

### 3.2 Create `pyproject.toml` (or `requirements.txt`) for `uv`
`uv` honours **PEP 508** markers and Poetry-style `pyproject.toml`. Choose **pyproject** for future Poetry compatibility:
```toml
[project]
name = "notion-agent"
version = "0.0.0"
dependencies = [
	"asyncio",  # stdlib but kept for clarity
	"aiohttp>=3.9,<4",
	"pydantic>=2.5,<3",
	# … copy entries from requirements-conda.txt
]

[project.optional-dependencies]
dev = [
	"pytest",
	"ruff",
]

[tool.uv]  # uv-specific overrides
index-url = "https://pypi.org/simple"
```

Put this file under `Agents/NotionAgent/pyproject.toml`.

---

## 4. Local Installation & Editable Links ✅ DONE
1. Ensure `tz_common` becomes an **editable** install so both Notion Agent and others load latest code:
	```bash
	uv pip install -e common/src
	```
2. Install project deps:
	```bash
	uv pip install -r requirements-conda.txt  # interim
	uv pip sync   # once pyproject is canonical
	```

---

## 5. Validation Matrix
| Check | Command | Expected |
|-------|---------|----------|
| Unit tests | `pytest Agents/NotionAgent/tests` | All pass |
| Lint | `ruff check Agents/NotionAgent` | No errors |
| Type check (optional) | `pyright Agents/NotionAgent` | No critical issues |

Automate via GitHub Actions matrix (`conda` vs `uv`). Only merge when `uv` lane is green.

---

## 6. Incremental Cleanup
1. Remove deprecated Conda-only packages from `pyproject`.
2. Update README & developer docs to mention `uv` workflow.
3. Add `.venv_uv_services` to `.gitignore`.

---

## 8. Rollback Strategy
1. Deactivate `.venv_uv_services` and `conda activate services`.
2. Ensure no `pyproject.toml` changes are merged if tests fail.
3. Revert git tag if needed:
	```bash
	git reset --hard notion_uv_migration_start
	```

---

## 10. Risk Register
1. **Binary wheels** missing on `uv` (edge cases) → Pin to previous wheel or compile via `pip install --no-binary`.
2. **Platform-specific packages** (e.g. `uvloop`) → Ensure proper markers.
3. **Editable install path** confusion → Use absolute paths in `uv pip install -e`.

---

## 11. Done Definition
- [ ] `pytest` passing under `uv`
- [ ] Documentation updated

---

*End of Plan* 