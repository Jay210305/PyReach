# SOURCE: impeccable

1. **Name:** impeccable (design-craft skill + anti-pattern detector)
2. **Upstream repository:** `pbakaus/impeccable`
3. **Upstream URL:** https://github.com/pbakaus/impeccable
4. **License:** Apache-2.0 (see `LICENSE`)
5. **Why it exists in Fulbo:** Frontend/UI design-craft and anti-pattern detection for the React/Vite client.
6. **How it was imported:** Copied from the upstream repo's `.agents/skills/impeccable/` (the Antigravity-format skill).
7. **Local modifications:** Yes. (a) Hardcoded `.agents/skills/impeccable/` script paths were rewritten to `.agents/skills/frontend/impeccable/` (15 files) after the move. (b) A UTF-8 BOM that an earlier rewrite introduced into 15 files was stripped (BOM breaks Codex's skill parser).
8. **Generated/runtime files:** The `scripts/impeccable` launcher downloads the engine binary at runtime (not vendored); `~/.impeccable/bin/` and a project `.impeccable/` workspace may be created at use time.
9. **Canonical vs adapter:** Canonical project content (portable skill).
10. **Update procedure:** `npx impeccable install` (or `npx impeccable update`), relocate into `.agents/skills/frontend/impeccable/`, and re-apply the path rewrite. Verify no BOM is reintroduced.
11. **Compatibility limitations:** The detector engine is a platform binary fetched at runtime (needs network on first use); the skill assumes a harness with shell access.
