# SOURCE: superpowers

1. **Name:** superpowers (development methodology skills)
2. **Upstream repository:** `obra/superpowers`
3. **Upstream URL:** https://github.com/obra/superpowers
4. **License:** MIT (see `LICENSE`)
5. **Why it exists in Fulbo:** A development methodology (brainstorming, planning, subagent-driven-development, TDD, systematic-debugging, code review, verification-before-completion) that structures how agents approach work.
6. **How it was imported:** Copied from the upstream repo's `skills/` directory (portable content only), including per-harness `references/*-tools.md`.
7. **Local modifications:** None to the skill files. A thin OpenCode bootstrap adapter at `.opencode/plugins/superpowers.js` injects `using-superpowers` (it does not re-register skills).
8. **Generated/runtime files:** None.
9. **Canonical vs adapter:** Canonical project content (portable skills). Native harness plugins exist separately (see below).
10. **Update procedure:** Re-run the per-harness native install (Agy `agy plugin install ...`; Codex `codex plugin add superpowers@openai-curated-remote`) and re-copy `skills/*` here.
11. **Compatibility limitations:** Native plugins ship their own copy of the skills; the portable copy here is the canonical project-visible source. The `using-superpowers` bootstrap references per-harness tool maps that must match each agent's tool names.
