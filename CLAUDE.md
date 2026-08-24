## Agent skills

### Issue tracker

Issues live as GitHub Issues in QeekOw/InForm, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Ponytail (minimal-code plugin)

Enabled project-wide via `.claude/settings.json` (`enabledPlugins`). Prefers the smallest correct solution (YAGNI → reuse → stdlib → native platform → existing dep → one-liner → custom code) before writing code. One-time setup per machine: `/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`.

### Graphify (Codebase Knowledge Graph)

This project contains a knowledge graph at `graphify-out/` mapping architecture, god nodes, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for tracing relationships and `graphify explain "<concept>"` for focused concepts.
- Read `graphify-out/GRAPH_REPORT.md` for broad architecture review and community structure.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, fast and free).

