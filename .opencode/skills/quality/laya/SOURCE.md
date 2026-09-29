# SOURCE: laya

1. **Name:** laya (quality / validation gate)
2. **Upstream repository:** `NandhaKishorM/laya`
3. **Upstream URL:** https://github.com/NandhaKishorM/laya
4. **License:** Laya is Apache-2.0 (see upstream); this SKILL.md is project-authored.
5. **Why it exists in Fulbo:** Provides an automated plan-quality signal (decomposition, atomicity, specificity, ambiguity) as a gate before implementation; not a proof of correctness.
6. **How it was imported:** This SKILL.md was authored for the project. The actual engine is the Python package `laya`, installed into the project-local `.laya-venv/` (Python 3.13). The MCP bridge is `.opencode/mcp/laya-mcp.mjs` + `.opencode/mcp/laya_worker.py`.
7. **Local modifications:** The bridge/worker are project-authored. `laya_worker.py` forces `HF_HUB_DISABLE_SYMLINKS=1` (Windows) and defaults `LAYA_PRELOAD=0`; `laya-mcp.mjs` auto-detects `.laya-venv`.
8. **Generated/runtime files:** `.laya-venv/` (gitignored) and the HuggingFace cache under `~/.cache/huggingface/hub/models--convaiinnovations--laya`.
9. **Canonical vs adapter:** Canonical project content (the skill documents the project-authored MCP adapter).
10. **Update procedure:** `uv pip install --python .laya-venv/Scripts/python.exe --upgrade laya`; recreate the venv with `uv venv --python 3.13 .laya-venv` if Python changes.
11. **Compatibility limitations:** Python 3.14 is unsupported by torch (use 3.13). Laya exposes only `laya_status` and `validate_plan` (no `validate_test`). The base checkpoint is near-chance zero-shot, so results are advisory and confidence-gated.
