# SOURCE: mcp-builder

1. **Name:** mcp-builder (MCP server development skill)
2. **Upstream repository:** `anthropics/skills` (subpath `skills/mcp-builder`)
3. **Upstream URL:** https://github.com/anthropics/skills/tree/main/skills/mcp-builder
4. **License:** See `LICENSE.txt` (Anthropic terms)
5. **Why it exists in Fulbo:** A reusable capability for designing, implementing, and evaluating MCP servers (this project already ships MCP bridges such as `fulbo-laya`).
6. **How it was imported:** Copied from the upstream repo (sparse checkout of `skills/mcp-builder`).
7. **Local modifications:** None.
8. **Generated/runtime files:** None (`scripts/evaluation.py` is authored upstream, not generated).
9. **Canonical vs adapter:** Canonical project content (portable skill). Note: this is a skill *for building* MCP servers, not an MCP server itself.
10. **Update procedure:** Re-fetch `anthropics/skills` and copy `skills/mcp-builder/*` here.
11. **Compatibility limitations:** References Python (FastMCP) and Node/TypeScript (MCP SDK) runtimes that must be installed at use time; not wired as an MCP server in this project.
