### Why it only blows up in the container

| Where it runs    | `openai`                       | `httpx`                                   | Result                            |
| ---------------- | ------------------------------ | ----------------------------------------- | --------------------------------- |
| **Your laptop**  | 1.35.10 (works with `proxies`) | 0.27.\* (still accepts `proxies`)         | ✅                                 |
| **Docker build** | 1.35.10 (same)                 | **0.28.0-latest** (dropped `proxies` arg) | ❌ `Client.__init__() … 'proxies'` |

`httpx 0.28.0` removed the long-deprecated `proxies` keyword. Older `openai` clients—including 1.35.10—still pass it, and LangChain just relays the kwargs. Fresh Docker builds pull the newest `httpx`, whereas your local venv still has 0.27.x, so you never saw the breakage. ([github.com][1], [community.openai.com][2])

### Fastest fixes (pick one)

| Option                                                   | What to change                                           | One-liner                                              |
| -------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------ |
| **A. Pin httpx** (zero code changes)                     | keep the exact libs you have, but force an older `httpx` | `pip install "httpx<0.28"` (add to `requirements.txt`) |
| **B. Upgrade openai (preferred)**                        | new OpenAI SDK ≥ 1.56.1 strips the `proxies` kwarg       | `pip install -U openai langchain-openai`               |
| **C. Upgrade both stacks**                               | latest everything works together                         | `pip install -U langchain langchain-openai openai`     |
| **D. Hot-patch (last resort)**                           | drop `proxies` before making the call                    | \`\`\`python                                           |
| from openai.\_base\_client import SyncHttpxClientWrapper |                                                          |                                                        |
| class \_NoProxy(SyncHttpxClientWrapper):                 |                                                          |                                                        |

```
def __init__(self,*a,**kw):
    kw.pop("proxies",None); super().__init__(*a,**kw)
```

````| :contentReference[oaicite:1]{index=1} |

### What to do next

1. **Freeze exact deps**  
   Keep a `requirements.txt` that pins *all* indirect deps (use `pip freeze > requirements.lock`). That guarantees Docker ≈ laptop.

2. **Check versions inside the image**  
   ```dockerfile
   RUN pip list | grep -E 'openai|httpx|langchain'   # sanity-check
````

3. **Watch for LangChain ≥ 0.2.10**
   Newer `langchain-openai` no longer forwards `proxies`, but it still requires the fixed OpenAI SDK. ([github.com][3])

### TL;DR

The container silently picked up **httpx 0.28.0**, which removed the `proxies` parameter that your current `openai`/LangChain combo still sends. Pin `httpx<0.28` **or** upgrade `openai` to ≥ 1.56.1 (and ideally bump LangChain) and the build will start cleanly.

[1]: https://github.com/langchain-ai/langchain/issues/28406 "Deprecated argument(s) removed when using `httpx==0.28.0` · Issue #28406 · langchain-ai/langchain · GitHub"
[2]: https://community.openai.com/t/client-openai-returns-error-client-init-got-an-unexpected-keyword-argument-proxies/1035249?utm_source=chatgpt.com "Client = OpenAI() returns error \"Client.__init__() got an unexpected ..."
[3]: https://github.com/langchain-ai/langchain/issues/28406?utm_source=chatgpt.com "Deprecated argument(s) removed when using httpx==0.28.0 #28406"
