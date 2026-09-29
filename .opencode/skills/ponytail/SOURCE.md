# SOURCE: ponytail

1. **Name:** ponytail (agent-optimization / lazy-senior-dev discipline)
2. **Upstream repository:** `DietrichGebert/ponytail`
3. **Upstream URL:** https://github.com/DietrichGebert/ponytail
4. **License:** MIT (see `LICENSE`)
5. **Why it exists in Fulbo:** Encourages minimal, YAGNI-first, root-cause fixes to reduce over-engineering across the project.
6. **How it was imported:** Copied from the upstream repo's `skills/` directory (portable SKILL.md files only).
7. **Local modifications:** None to the skill files. The concise always-on ruleset (upstream `.agents/rules/ponytail.md`) is also vendored at `.agents/rules/ponytail.md`, and a thin OpenCode adapter at `.opencode/plugins/ponytail.js` injects it into the system prompt.
8. **Generated/runtime files:** None (the OpenCode adapter is hand-written, not generated).
9. **Canonical vs adapter:** Canonical project content (portable skills) plus a thin OpenCode adapter.
10. **Update procedure:** Re-fetch upstream, re-copy `skills/*` here, and reconcile `.agents/rules/ponytail.md` with upstream's `.agents/rules/ponytail.md`.
11. **Compatibility limitations:** The upstream MCP server (`ponytail-mcp/`) was deliberately not installed (user-invoked; duplicates the ruleset). Codex has no official Ponytail plugin in its marketplace, so Codex is served by the portable skills only.
