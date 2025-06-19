**Root of the new failure**

Your *local ≠ Docker* gap is no longer `httpx`—it’s a **stale `langchain-openai`** that still tacks `proxies=` onto the OpenAI constructor.
Inside the container pip is upgrading `openai` (because `langchain-openai 0.1.14` asks for ≥ 1.40) but *not* upgrading itself, so you end up with:

| pkg                  | pulled in container                     | still does what? |
| -------------------- | --------------------------------------- | ---------------- |
| **openai**           | 1.56-plus (no longer accepts `proxies`) | 💥               |
| **langchain-openai** | 0.1.14 (still *sends* `proxies`)        | 💥               |

That combination always explodes, no matter how you pin `httpx`.
See the LangChain issue that calls this out: “update the SDK **and** langchain-openai; only one won’t help” ([github.com][1]).
And note the OpenAI 1.56.1 changelog (“dropped `proxies`; works with httpx 0.28+”) ([github.com][2]).

---

### What to do

| fix                                          | commands   | comment |
| -------------------------------------------- | ---------- | ------- |
| **✅ Upgrade both libs (recommended)**        | \`\`\`bash |         |
| pip install -U "langchain-openai>=0.2.10" \\ |            |         |

```
           "openai>=1.56.1" \
           "httpx>=0.28"
```

``| `langchain-openai ≥ 0.2.10` stopped forwarding `proxies`, so the pair is in sync again. | | **🩹 Stay on old stack** |``bash
pip install "langchain-openai==0.1.8"&#x20;
"openai<1.56"&#x20;
"httpx<0.28"

````| 0.1.8 was the last tag **before** the OpenAI ≥ 1.40 requirement. |
| **🚫 Kill the proxy flag at runtime** | ```python
ChatOpenAI(..., openai_proxy=None)     # overrides env
``` | Works even with mixed versions, but you lose proxy support. |
| **🔒 Freeze exactly what you run** | after the build: `pip freeze > requirements.lock` | Guarantees Docker == laptop next time. |

---

### Why earlier ideas failed

| idea | status |
|------|--------|
| **Pin `httpx<0.28` only** | Still exploded because OpenAI ≥ 1.56 rejects `proxies`. |
| **Upgrade OpenAI only** | 0.1.14 kept sending `proxies`, so nothing changed. |
| **Exact-version pin from laptop** | Pip silently *upgraded* OpenAI to satisfy `langchain-openai 0.1.14`’s spec, undoing your pin. |

---

### Quick smoke-test inside the image

```dockerfile
RUN python - <<'PY'
import importlib.metadata, sys, os
for pkg in ("openai", "langchain_openai", "httpx"):
    print(pkg, importlib.metadata.version(pkg))
print("OPENAI_PROXY =", os.getenv("OPENAI_PROXY"))
PY
````

If you still see `openai >=1.56` together with `langchain_openai 0.1.x`, your requirements are being overruled.

---

**TL;DR**
Upgrade **both** `langchain-openai` **and** `openai` (or downgrade both); then rebuild. That removes the last stray `proxies=` and the container starts cleanly.

[1]: https://github.com/langchain-ai/langchain/issues/28560 "Validation Error: __init__() got an unexpected keyword argument 'proxies' in OpenAIEmbeddings · Issue #28560 · langchain-ai/langchain · GitHub"
[2]: https://github.com/langchain-ai/langchain/issues/28560?utm_source=chatgpt.com "Validation Error: __init__() got an unexpected keyword ... - GitHub"
