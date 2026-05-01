---
id: KB-2026-032
type: research
status: active
created: 2026-05-01
updated: 2026-05-01
tags: [task-specification, knowledge-graph, karpathy, graphify, agents-md, context-building]
related: [KB-2026-031, KB-2026-030]
---

# Graphify and the Karpathy Wiki Method: Application to Agent Task Specs

## Purpose

Evaluate two emerging techniques — Graphify (knowledge graph for codebases) and
Karpathy's LLM Wiki method — for improving how aider-relay task specs are written
and served to autonomous coding agents.

---

## Technique 1: Graphify

### What it is

An open-source AI coding assistant skill (github.com/safishamsi/graphify, April 2026,
22k stars in 10 days). Converts a codebase + docs into a queryable knowledge graph in
three passes:

1. AST pass via Tree-sitter — extracts code structure (classes, functions, imports,
   call graphs) locally, no LLM, no network.
2. Audio/video transcription via faster-whisper (local).
3. Claude subagents in parallel over docs/papers/images → concepts + relationships
   merged into a NetworkX graph via Leiden clustering (topology-based, no embeddings).

Outputs:
- **`GRAPH_REPORT.md`** — the agent-facing summary (what agents actually read)
- **`graph.json`** — persistent graph, SHA256 change-tracked
- Interactive HTML graph for humans

For Claude Code it writes `CLAUDE.md` + a `PreToolUse` hook in `settings.json` that
injects: "graphify: Knowledge graph exists. Read GRAPH_REPORT.md for god nodes and
community structure before searching raw files." For Aider it writes to `AGENTS.md`.

### GRAPH_REPORT.md structure (four sections)

| Section | Content |
|---|---|
| God Nodes | 5-10 most central concepts — what agents must understand first |
| Surprising Connections | Cross-file links with explanations |
| Suggested Questions | 4-5 things the graph can answer uniquely |
| Design Rationale | Extracted from docstrings and comments |

### Evidence

Self-reported: 71.5x token reduction per query on a 52-file mixed corpus (code + papers
+ images) vs naively loading all raw files. Methodology is transparent (worked examples
in repo) but not independently peer-reviewed. The headline number compares against the
worst baseline — treat as "significant compression on medium-large repos."

Broader GraphRAG evidence (arXiv 2502.11371, systematic evaluation, Feb 2025): GraphRAG
and plain RAG have "distinct strengths" — neither dominates. GraphRAG wins decisively on
dependency/relationship queries (8.1x in one benchmark), which are common in coding
("what touches the auth module?"). Straightforward factual retrieval: plain RAG is
competitive.

Related lighter-weight alternative: **lat.md** (github.com/1st1/lat.md) — adds a
`lat.md/` directory of interlinked markdown files with wiki-style links
(`[[src/auth.ts#validateToken]]`) and backlinks from source comments. Agents use CLI
commands (`lat search`, `lat expand`, `lat section`) rather than a pre-built report.

### What to borrow for TASK.md

- **God nodes concept**: explicitly name the 5-10 most central concepts an agent must
  understand before starting. Put these near the top of the spec.
- **EXTRACTED / INFERRED (confidence: 0.0-1.0) / AMBIGUOUS** relationship tagging:
  distinguish known facts from beliefs when making claims about code structure in specs.
- **PreToolUse hook pattern**: steer agents toward structural context *before* file
  searching, not after — relevant to how aider-relay injects context at session start.
- **Auto-generation**: for each new autonomous session, run Graphify to produce the
  structural orientation section of the TASK.md, replacing hand-written codebase
  orientation boilerplate.

### Verdict

**Partially useful, specific application window.** Best for medium-large repos where
flat prose orientation becomes stale or incomplete. For aider-relay itself (moderately
complex Python hard fork), Graphify or lat.md could automate the structural orientation
section of task specs. Not a spec-writing philosophy — a practical automation tool.

---

## Technique 2: Karpathy LLM Wiki Method

### What it is

Andrej Karpathy published a GitHub Gist on 2026-04-04
(gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): an "idea file" — a
markdown document to paste into Claude Code / Codex / OpenCode, which then instantiates
the pattern for your specific needs. Deliberately left abstract to allow many directions.

Core concept: instead of RAG infrastructure, maintain a curated directory of plain
markdown files — the "wiki" — that an LLM maintains, queries, and audits. Human
provides sources and asks questions; LLM does all bookkeeping, cross-referencing,
maintenance.

### Three-layer architecture

| Layer | Directory | Ownership |
|---|---|---|
| Immutable sources | `raw/` | Human — LLM reads, never modifies |
| Maintained knowledge | `wiki/` | LLM — summaries, entity pages, synthesis |
| Process definition | `CLAUDE.md` / `AGENTS.md` | Human — structure, ingest rules, query format, lint |

### Three core operations

- **Ingest**: On new source — LLM reads it, updates 10-15 existing wiki pages, appends
  to `log.md`
- **Query**: LLM synthesises from wiki pages with citations; valuable discoveries filed
  as new pages
- **Lint**: Periodic — find contradictions, orphaned pages (no inbound links), stale
  claims, missing cross-references

### Two special files

- **`index.md`**: Content-oriented catalog by category, each entry with one-line
  summary + metadata. Agent's table of contents.
- **`log.md`**: Append-only chronological record with consistent prefixes
  (`## [2026-04-02] ingest | Title`) for parseability.

### LLM Wiki v2 extensions (rohitg00, community gist)

Adds: confidence scoring on facts, Ebbinghaus-model retention curves (fading for
un-reinforced facts), typed relationships (`uses`, `contradicts`, `caused`), hybrid
search (BM25 + embeddings + graph traversal) for scale beyond ~500 pages.

### Evidence

No independent controlled study. Evidence: (a) wide community uptake within weeks,
(b) multiple independent implementations confirm it works as described, (c) theoretical
soundness — replaces retrieval-time inference with pre-computed, human-verified
structure, a well-established tradeoff.

Scale ceiling: ~200-500 wiki pages before full-context loading breaks down. Beyond
that, hybrid RAG is needed. The "70x more efficient than RAG" claim in blog posts refers
to eliminating RAG infrastructure overhead, not token reduction — not an apples-to-apples
comparison.

### What to borrow for TASK.md

The schema document (the `CLAUDE.md` / `AGENTS.md`) is described as "the most important
file in the system" — it defines *operations*, not just *facts*. This is the key insight.

| Wiki convention | TASK.md application |
|---|---|
| `raw/` vs `wiki/` split | Mark sections `[IMMUTABLE]` vs `[AGENT-MAINTAINED]` — background context vs working context the agent can update during the session |
| `index.md` with one-line summaries | For large spec files: add an orientation table at the top with section name + one-line purpose |
| Lint operation | Add "spec lint" step: before starting, agent checks spec for contradictions, undefined terms, missing cross-references |
| `log.md` append-only pattern | Session log with structured prefixes — audit trail for long autonomous runs |
| Schema = process definition | TASK.md "Workflow" section should define *operations* (allowed actions + decision rules), not just task description |
| Typed relationships (v2) | For multi-agent specs, name relationship types between components: "A uses B", "C contradicts D" |

### Verdict

**Worth incorporating, selectively.** The most valuable contribution is the framing:
the schema/config document defines *operations*, not just *facts*. This directly
improves how TASK.md files should be written. The structural conventions (index, log,
immutable/mutable split, lint) are adoptable without the full wiki infrastructure.
Full three-layer setup is more relevant for persistent cross-session knowledge bases
than per-task specs.

---

## Synthesis: How These Two Techniques Relate

Graphify explicitly positions itself as materialising the Karpathy wiki concept for
codebases (see: "From Karpathy's LLM Wiki to Graphify", Analytics Vidhya). They are
complementary, not competing:

- **Karpathy wiki conventions** → structure your TASK.md format (index, log,
  schema-as-process-definition, lint, immutable/mutable split)
- **Graphify / lat.md** → automate the structural orientation section (god nodes, key
  relationships, design rationale), replacing manual codebase boilerplate

Neither requires full infrastructure adoption to get value. The structural conventions
are the portable part.

### Recommended additions to the KB-2026-031 TASK.md template

```markdown
## Orientation
<!-- Auto-generated or hand-written: name the 5-10 god nodes the agent must understand first -->
- God nodes: [AuthProvider, relay_loop.py, MTARPSession, ...]
- Key relationship: AiderProvider wraps Coder via asyncio.to_thread()
- Non-obvious: exhaustion detection is at the provider tier, not the model tier

## Agent Log
<!-- Append-only; agent writes a line here after each logical unit of work -->
- [start] Beginning task
```

---

## Sources

- [Graphify GitHub (safishamsi/graphify)](https://github.com/safishamsi/graphify)
- [Karpathy llm-wiki Gist (2026-04-04)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LLM Wiki v2 community extension (rohitg00)](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)
- [From Karpathy's LLM Wiki to Graphify (Analytics Vidhya)](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/)
- [lat.md: Agent Lattice knowledge graph in markdown](https://github.com/1st1/lat.md)
- [RAG vs. GraphRAG Systematic Evaluation (arXiv 2502.11371, Feb 2025)](https://arxiv.org/abs/2502.11371)
- [What Is Karpathy's LLM Wiki? (MindStudio)](https://www.mindstudio.ai/blog/karpathy-llm-wiki-knowledge-base-claude-code)
- [Build Personal Knowledge Base 70x Faster Than RAG (MindStudio)](https://www.mindstudio.ai/blog/karpathy-llm-wiki-pattern-personal-knowledge-base-without-rag)
