# Agent Guidelines for InForm

## Domain Context
- Authoritative domain terminology is defined in `CONTEXT.md`.
- Architectural decisions are in `docs/adr/`.
- Issues are tracked via GitHub Issues (`gh` CLI). See `docs/agents/issue-tracker.md`.

## Graphify (Codebase Knowledge Graph)

This project has a knowledge graph at `graphify-out/` mapping architecture, god nodes, community structure, and cross-file relationships.

Rules:
- For codebase and architectural questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- Read `graphify-out/GRAPH_REPORT.md` for broad architecture review, god nodes, and community structure.
- After modifying code files, run `graphify update .` to keep the graph current (AST-only, no API cost).
