# SOURCE: taste

1. **Name:** taste (anti-slop frontend design skills)
2. **Upstream repository:** `Leonxlnx/taste-skill`
3. **Upstream URL:** https://github.com/Leonxlnx/taste-skill
4. **License:** MIT (see `LICENSE`)
5. **Why it exists in Fulbo:** Anti-slop frontend design guidance (design-taste-frontend, minimalist, brutalist, soft, redesign, image-to-code, brandkit, imagegen) for landing pages and redesigns.
6. **How it was imported:** Copied from the upstream repo's `skills/` directory.
7. **Local modifications:** Yes. Skill directories were renamed to match their frontmatter `name` (OpenCode requires `name == directory`), e.g. `minimalist-skill/` -> `minimalist-ui/`. The upstream `llms.txt` index was removed (stale names). Skill body text is otherwise unchanged.
8. **Generated/runtime files:** None.
9. **Canonical vs adapter:** Canonical project content (portable skills).
10. **Update procedure:** Re-fetch upstream, copy `skills/*` here, re-apply directory renames to match `name`, and re-run the `name == directory` check.
11. **Compatibility limitations:** The `design-taste-frontend` skill references an upstream `skills/taste-skill/blocks/` path that does not exist here (upstream aspirational block library); the reference is inert prose.
