**Yes — you can keep using `uv`, you just have to treat it as a custom tool that Codex installs during the *setup-script* phase.**
Out of the box Codex still looks only for the classic files (`requirements.txt`, `Pipfile`, `pyproject.toml`, …) and runs `pip` behind the scenes, so an explicit setup step is needed.([openai.com][1])

---

### Quick recipe

1. **Commit a setup script** (e.g. `.codex/setup.sh`) that:

   ```bash
   #!/usr/bin/env bash
   # Install uv (single static binary) – runs while the sandbox still has net
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Re-create the venv exactly as on your laptop
   uv sync          # reads pyproject.toml + uv.lock
   ```
2. In **Environment → Advanced → Shell setup script** point to that file, or add

   ```text
   setup: bash .codex/setup.sh
   ```

   inside your repository’s `AGENTS.md`.
3. Tell Codex how to run the tests, e.g. `uv run pytest -q` (or just `pytest` if you activate the venv in the script).

That’s it: the agent will download `uv`, recreate your lockfile, and then run the task inside the regenerated venv.

---

### What to know before you hit “Run”

| Detail                                                                                                                                                                                           | Why it matters |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| **Setup happens once per environment** and is cached; subsequent tasks reuse the venv, so the few-second `uv sync` cost is paid only on cold start.                                              |                |
| **Internet is cut *after* setup**; any package fetches must happen inside the script.([openai.com][1])                                                                                           |                |
| Codex **does not parse `uv.lock` on its own**; without the script it will fall back to empty-env + `pip install -r requirements.txt` and likely fail.                                            |                |
| `uv` can pin the Python interpreter, but Codex’s base images currently expose 3.8 or 3.10 only. If you need, say, 3.7, prepend `pyenv install 3.7.17 && pyenv global 3.7.17` in the same script. |                |
| For hermetic builds, commit wheels or use a private index token via the Secrets panel (`--extra-index-url $PIP_PRIVATE`).                                                                        |                |

---

### Alternatives if you want zero custom scripting

*Run `uv` locally but let Codex stick to pip.*

```bash
uv pip compile --universal --output-file requirements.txt
git add requirements.txt
```

Codex will now install from that file automatically, and you still use `uv` day-to-day. This is simpler, but you lose the speed of `uv sync` inside the sandbox.

---

### TL;DR

*Codex doesn’t mind what installs your deps, it just needs everything ready before the agent starts running code. A one-liner that installs `uv` and calls `uv sync` in the setup script is all it takes.*

Refs: `uv` install instructions([github.com][2]), Heroku buildpack announcement showing growing first-class support for `uv` in build systems (same idea as the script above)([devcenter.heroku.com][3]), community guidance on using the setup-script window to add custom tooling in Codex sandboxes([community.openai.com][4]).

[1]: https://openai.com/index/introducing-codex/ "Introducing Codex | OpenAI"
[2]: https://github.com/astral-sh/uv "GitHub - astral-sh/uv: An extremely fast Python package and project manager, written in Rust."
[3]: https://devcenter.heroku.com/changelog-items/3238?utm_source=chatgpt.com "Python buildpacks now support the package manager uv"
[4]: https://community.openai.com/t/codex-cloud-environment-for-build-and-run-unit-tests/1263843?utm_source=chatgpt.com "Codex (Cloud) environment for build and run unit tests?"
