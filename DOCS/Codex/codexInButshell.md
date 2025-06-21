**OpenAI Codex in a nutshell**

* **What it is** – A cloud-hosted software-engineering agent powered by the new *codex-1* variant of the o3 model. Each job you give it (--“write this feature”, “fix that bug”, “run the tests”--) spins up an **isolated Linux sandbox** that already contains your repo and lets the agent run shell commands, edit files and push a PR. ([openai.com][1], [wsj.com][2])

* **Why it matters** – The agent can loop until the test suite is green and shows every command it executed, so you can audit its work before merging. ([openai.com][1])

---

### 1  Running your unit tests in the cloud sandbox

1. **Point Codex at your repository** (GitHub, GitLab, or a ZIP upload).
2. **Tell it how to run the tests**. Two common ways:

   | Option        | Where to configure                                                                               | Example                  |
   | ------------- | ------------------------------------------------------------------------------------------------ | ------------------------ |
   | *Zero-config* | Keep a `pytest`, `npm test`, or `make test` target in your repo; Codex auto-detects and runs it. | `pytest -q`              |
   | *Explicit*    | Add a line in **AGENTS.md** or the *Test command* field under *Environment → Edit → Advanced*.   | `scripts/ci/run_unit.sh` |

   The agent streams the test logs to the UI; failures are visible both to you and to the model so it can iterate. ([community.openai.com][3])

---

### 2  Managing dependencies

| Layer                       | How Codex handles it                                                                                                                 | Tips for older Python stacks                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| **Base image**              | Choose Python 3.8 or 3.10 in *Environment → Language version*. For versions < 3.8 you’ll need a custom Dockerfile.                   | Add `Dockerfile` that installs, e.g., `pyenv install 3.6.15` and set `python3` accordingly.                |
| **Package install**         | Codex auto-detects `requirements.txt`, `Pipfile`, `pyproject.toml`, `environment.yml`, etc., and runs the matching install command.  | Pin exact versions (`==`) and include wheels or a private index if the packages have been yanked upstream. |
| **Custom steps**            | Put any `apt-get`, `conda`, or `pip` commands in the **Setup script** field (runs once per environment, cached). ([instructa.ai][4]) | Use the setup script to grab legacy libs, build C-extensions, or patch build flags.                        |
| **Secrets / private repos** | Add tokens under *Environment → Secrets*; they’re injected as env vars for `pip install`.                                            | Same workflow—just be sure the installer reads the secret (e.g., `--extra-index-url $PIP_PRIVATE`).        |

*Gotcha*: A recent forum thread notes that if you install deps interactively the agent won’t “see” them unless they’re also in the setup script or lock-file committed to the repo. ([community.openai.com][5])

---

### 3  Checklist for legacy Python projects

1. **Freeze the exact versions** (`pip freeze > requirements.txt`).

2. **Commit wheels or tarballs** for any packages no longer on PyPI.

3. **Create a minimal setup script**:

   ```bash
   # .codex/setup.sh
   pyenv install 3.7.17 --skip-existing
   pyenv global 3.7.17
   pip install -r requirements.txt
   ```

4. In *Environment → Advanced* set “Shell setup script” to `bash .codex/setup.sh`.

5. Put the command to run your tests in AGENTS.md if it isn’t the default.

With that in place Codex will build the env once, cache it, and re-use it for every task.

---

**Bottom line**

Running tests in Codex is as simple as committing a reproducible environment (lock file or setup script) and telling the agent what counts as “green”. Even projects that depend on decade-old Python libraries can work--you just have to pin and pre-install those deps in the setup phase.

[1]: https://openai.com/index/introducing-codex/?utm_source=chatgpt.com "Introducing Codex - OpenAI"
[2]: https://www.wsj.com/articles/openai-launches-new-ai-coding-agent-c8dabc60?utm_source=chatgpt.com "OpenAI Launches New AI Coding Agent"
[3]: https://community.openai.com/t/codex-cloud-environment-for-build-and-run-unit-tests/1263843?utm_source=chatgpt.com "Codex (Cloud) environment for build and run unit tests?"
[4]: https://www.instructa.ai/blog/this-is-how-i-use-openai-codex-swe-agent?utm_source=chatgpt.com "This is how I use OpenAI Codex Agent | Instructa Courses"
[5]: https://community.openai.com/t/codex-python-dependencies-install-but-agent-cant-see-them/1268801?utm_source=chatgpt.com "Codex: Python dependencies install, but agent can't see them"
