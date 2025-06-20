# Dockerize Notion REST Server – UV-Based Plan

## Context & Goals
This plan supersedes the earlier `dockerize-rest-server.md`.  The version-pinning conflicts that caused the previous build to fail have been fixed via the **`.venv_uv_tz`** environment and exact dependency pins recorded in `pyproject.toml` / `requirements.txt`.

Key goals:
1. Build a lean, reproducible Docker image that isolates **Notion Agent** together with the shared **tz_common** package.
2. Use **uv** as the package manager inside the container to recreate the *exact* environment defined by `.venv_uv_tz`.
3. Keep development parity: the same `uv` workflow (venv + editable installs) should work both locally and in the container.
4. Persist logs and expose the REST API on port **8000**.

## High-Level Changes vs Previous Plan
| Area | Old Plan | New Plan |
|------|---------|----------|
| Python env | `pip install -r requirements.txt` inside global interpreter | Create `.venv_uv_tz` in the container and manage packages with **uv** |
| Package manager | `pip` | `uv` |
| Dependency source | `requirements.txt` only | Primary: `pyproject.toml` + `uv pip sync` (falls back to `requirements.txt` for legacy) |

---

## Implementation Phases

### Phase 0 – Prep
* Confirm `.venv_uv_tz` is committed and **passes all tests** locally.
* Verify `pyproject.toml` and `requirements.txt` are in sync (they are the single source of truth for uv).

### Phase 1 – Dockerfile Rewrite
1. **Base image**: `python:3.11-slim` (keeps Pydantic v1 compatibility).
2. **Install uv**:
   ```dockerfile
   RUN pip install --no-cache-dir uv
   ```
3. **Create venv & install deps**:
   ```dockerfile
   # Create the exact same venv name used in development
   RUN uv venv /opt/.venv_uv_tz
   ENV PATH="/opt/.venv_uv_tz/bin:$PATH"

   # Copy dependency manifests first for better layer caching
   COPY Agents/NotionAgent/requirements.txt ./
   COPY Agents/NotionAgent/pyproject.toml ./
   RUN uv pip sync  # installs runtime deps into the venv
   ```
4. **Copy sources**:
   ```dockerfile
   COPY common/src ./tz_common/src
   COPY Agents/NotionAgent/Agent ./Agent
   COPY Agents/NotionAgent/operations ./operations
   COPY Agents/NotionAgent/launcher ./launcher
   ```
5. **Editable installs** (retain hot-reloading during local volume mounts):
   ```dockerfile
   RUN uv pip install -e ./tz_common/src
   RUN uv pip install -e .  # installs NotionAgent itself
   ```
6. **Entrypoint & healthcheck** unchanged except for activating the venv path (already on PATH).

> 💡 *Why keep a venv in a container?*  The extra isolation avoids polluting the base interpreter, making layer-caching safer when multiple projects share the same base image.

### Phase 2 – docker_compose.yaml Update
```yaml
env_file:
  - .env
environment:
  # Ensure venv binaries are found first
  - PATH=/opt/.venv_uv_tz/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
  - PYTHONPATH=/app:/app/tz_common
volumes:
  - ./logs:/app/logs
```
*No changes to ports, restart policy or health-check.*

### Phase 3 – Development Workflow
1. **Rebuild** whenever dependencies change:
   ```bash
   docker compose -f Agents/NotionAgent/docker_compose.yaml build --no-cache
   ```
2. **Run**:
   ```bash
   docker compose -f Agents/NotionAgent/docker_compose.yaml up -d
   ```
3. **Interactive shell inside venv**:
   ```bash
   docker exec -it notion-rest-server bash
   # venv already active via PATH
   python -m pytest  # run tests inside container if needed
   ```

### Phase 4 – Validation Checklist
- [ ] `docker compose build` succeeds without network access (all pins resolve from PyPI cache).
- [ ] Container health-check reports `healthy`.
- [ ] `curl http://localhost:8000/health` returns 200.
- [ ] All agent unit tests pass inside the container *(optional but recommended)*.

### Phase 5 – Documentation
After successful build & run:
1. Update `README.md` Docker section.
2. Update any developer docs referencing the old pip-based workflow.
3. Archive this plan by moving it to `TASKS/DONE/` once executed.

---

## Updated Dockerfile (pseudo-diff)
```diff
- RUN pip install -r requirements.txt
+ RUN pip install --no-cache-dir uv
+ RUN uv venv /opt/.venv_uv_tz
+ ENV PATH="/opt/.venv_uv_tz/bin:$PATH"
+
+ # Install deps via uv
+ COPY Agents/NotionAgent/pyproject.toml ./
+ COPY Agents/NotionAgent/requirements.txt ./
+ RUN uv pip sync
+
+ # Editable installs remain unchanged
+ RUN uv pip install -e ./tz_common/src && uv pip install -e .
```

## Updated docker_compose.yaml (snippet)
```diff
     volumes:
       - ./logs:/app/logs
+    environment:
+      - PATH=/opt/.venv_uv_tz/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
+      - PYTHONPATH=/app:/app/tz_common
```

---

## Definition of Done
1. Image builds & container runs with **no version mismatch errors**.
2. REST server reachable at `http://localhost:8000/health`.
3. Log files persist via volume mount.
4. Plan moved to `TASKS/DONE/` after user confirmation.

---
*End of plan – no code files were modified.* 