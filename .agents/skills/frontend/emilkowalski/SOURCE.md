# SOURCE: emilkowalski

1. **Name:** emilkowalski (frontend/UI design-engineering skills)
2. **Upstream repository:** `emilkowalski/skill`
3. **Upstream URL:** https://github.com/emilkowalski/skill
4. **License:** MIT (see `LICENSE`)
5. **Why it exists in Fulbo:** Reusable frontend/UI expertise (design philosophy, animation decision framework, UI-library selection, prototype, review) that complements the Fulbo-specific `project/frontend-development` skill.
6. **How it was imported:** Copied verbatim from the upstream repo's `skills/` directory into `.agents/skills/frontend/emilkowalski/<name>/`.
7. **Local modifications:** None (verbatim copies).
8. **Generated/runtime files:** None.
9. **Canonical vs adapter:** Canonical project content (portable skills).
10. **Update procedure:** Re-fetch upstream and re-copy `skills/*` here, preserving one subdirectory per skill; re-run the `name == directory` check. (`npx skills add emilkowalski/skill` installs flat and must be relocated.)
11. **Compatibility limitations:** Several skills target mobile/Swift (`write-swift`, `mobile-native`); they are frontend-adjacent and retained for completeness even though the Fulbo frontend is React/Vite.
