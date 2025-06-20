# Simplify Dependencies Plan – Notion Agent

## Goal
Shrink the `pyproject.toml` of *Notion Agent* to **only** the third-party libraries that are actually imported in its source code and tests while keeping the exact pinned versions that are already specified.  The work is done in a fresh **uv** environment called `.venv_uv_tz`.

> This plan follows the guidelines in `uv-migration-plan.md`.  Execute steps sequentially and record findings as you progress.

---

## 1. Safety & Preparation
1. Ensure the Conda `services` env is **deactivated**.
3. From repository root:
	```bash
	pipx ensurepath   # if not already
	```

---

## 2. Create Clean uv Environment
```bash
uv venv .venv_uv_tz
# Windows
.\.venv_uv_tz\Scripts\activate
```
Pin the interpreter version in `.python-version` if not already present.

---

## 3. Inventory Actual Imports
Run a quick static scan to list **external** imports used by Notion Agent:
```bash
python - <<'PY'
from pathlib import Path, PurePosixPath
import ast, json, sys

ROOT = Path('Agents/NotionAgent')
external = set()
for py in ROOT.rglob('*.py'):
    tree = ast.parse(py.read_text('utf-8'), filename=str(py))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                external.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.module.startswith(('Agents', 'operations', 'launcher', 'tests', 'tz_common')):
                external.add(node.module.split('.')[0])
print(json.dumps(sorted(external), indent=2))
PY
```
Manually map each discovered root module → PyPI package name.  Keep only packages that appear.

> ☑️ Save the mapping results under `Agents/NotionAgent/TASKS/import-inventory.json` for traceability.

---

## 4. Draft Minimal `pyproject.toml`
1. Copy the current `Agents/NotionAgent/pyproject.toml` to `pyproject.toml.bak` for reference.
2. Create a **new** `pyproject.toml` with sections:
	* `[build-system]` (same as before)
	* `[project]` – **dependencies** list replaced by minimal set from step 3, preserving version specifiers.
	* `[project.optional-dependencies]` – keep only `dev` with `pytest`, `ruff`, `mypy`.
	* `[tool.pytest]`, `[tool.uv]`, `[tool.setuptools]` – copy unchanged.

---

## 5. Install & Validate
```bash
uv pip sync       # installs according to new pyproject
uv pip install -e common/src   # editable install for shared lib
pytest Agents/NotionAgent/tests  -q
```

Iterate:
* If tests fail with `ImportError`, identify the missing package, add it **with the exact version** from the old `pyproject.toml`, run `uv pip sync`, and re-test.
* Repeat until the entire test suite passes.

---

## 6. Clean-Up
* Remove any packages that were added but remain unused (confirm with another static scan + tests).
* Update `README.md` & developer docs to describe `.venv_uv_tz` workflow.
* Add `.venv_uv_tz/` to `.gitignore` if missing.

---

## 7. Rollback Strategy
Should anything break:
```bash
mv pyproject.toml.bak Agents/NotionAgent/pyproject.toml
uv deactivate && rm -rf .venv_uv_tz
conda activate services   # fallback env
```

---

## 8. Definition of Done
- [x] Minimal `pyproject.toml` committed.
- [x] `.venv_uv_tz` builds with `uv pip sync`.
- [x] `pytest Agents/NotionAgent/tests` passes in the new env.
- [ ] User confirms that manual tests with Marimo Dashboard work.
- [x] Documentation updated.

---

*End of plan* 