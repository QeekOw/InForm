## Agent skills

### Issue tracker

Issues live as GitHub Issues in QeekOw/Strive, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Ponytail (minimal-code plugin)

Enabled project-wide via `.claude/settings.json` (`enabledPlugins`). Prefers the smallest correct solution (YAGNI → reuse → stdlib → native platform → existing dep → one-liner → custom code) before writing code. One-time setup per machine: `/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`.
