---
title: Drifter SOW — Framework Improvement Program v3
type: reference
version: "3.0"
status: draft
phase: "3"
created: '2026-10-06T00:00:00Z'
updated: '2026-10-07T12:00:00Z'
---

# Scope of Work — Drifter Framework Improvement Program (v3)

**Project:** Drifter — Universal AI Agent Drift Guard
**Repository:** https://github.com/Theohox/Drifter
**Reference documents:** "Ultimate AI Coding Agent Framework Checklist" (35 sections); Drifter Wiki v1.3; aider repo-map design; convaiinnovations/laya model card; 2026 SDD tooling landscape (Spec Kit, OpenSpec, BMAD, Kiro, Backlog.md); EARS / Gherkin / ISO 29148 / ISO 25010 requirements-engineering practice
**Date:** 2026-10-07 (revised, v3)
**Status:** Draft for review

**Changelog v3:** Added §4.0 Leverage-First Mandate and a build-vs-leverage matrix for every workstream — no bespoke implementation where a maintained OSS project already solves the problem (Spec Kit constitutions, MADR, Backlog.md task format, import-linter/dependency-cruiser, pip-audit/OSV/Scancode/OpenSSF, StrictDoc-style traceability, in-toto/SLSA attestation). Repositioned Drifter as the **enforcement layer beneath spec-authoring tools** rather than a competitor. Upgraded requirements management (W2) to full BSA/PM methodology: user stories, functional/non-functional split (ISO 25010), EARS system requirements, Gherkin acceptance criteria, MoSCoW priorities, INVEST validation, Definition of Ready/Done, UAT sign-off. Added checks `requirement_quality`, `uat_signoff`, `dod_gate`. Added interoperability acceptance criteria.

**Changelog v2:** Added Phase 0 (human decision foundations + inception Q&A). Revised W10 to an aider-style repo map. Added MCP-first rule. Added W20 optional calibrated-decision plugin (`drifter[decide]`) trained on Drifter's own audit data.

---

## 1. Background

Drifter is a pip-installable governance layer that constrains AI coding agents through enforced protocols: a 7-step pre-flight checklist, 35 automated drift checks, a document type system, shell command boundaries (`ShellGuard`), HMAC-signed session audits, a project conductor, and git pre-commit hooks.

The reference checklist defines a broader governance framework for AI-assisted development, organized around one principle: **AI is never the source of truth — the repository, tests, requirements, decisions, and human approvals provide the evidence.**

Three additional principles adopted in v2/v3:

- **Human decisions are upstream of drift.** Most drift originates at inception: tools chosen because they were easy rather than correct, limitations never recorded, scaling assumptions never tested. The framework must capture *why* decisions were made — "what is correct vs. what is easy, and why" — before it can police drift against them.
- **Borrow proven mechanisms, don't reinvent them.** Where a maintained OSS project has already solved a sub-problem (Spec Kit's constitution, aider's repo map, import-linter's layer contracts, MADR templates, Backlog.md task files), Drifter adopts or wraps it. Bespoke code is justified only where no wheel exists.
- **Drifter's defensible niche is enforcement, not authoring.** The 2026 spec-driven-development landscape (Spec Kit, OpenSpec, BMAD, Kiro) generates specs, plans, and tasks — but none of them make the spec *govern* the code or verify the result. Their documented weakness (static specs, drift managed by hand, no built-in verification) is precisely Drifter's reason to exist. Drifter ingests their artifacts and enforces them.

## 2. Objectives

1. Make **human decision-making a first-class, machine-checkable artifact**: an inception interview that forces explicit answers about tooling, fitness, limitations, scaling, and evidence — captured as constitution and ADRs before agents write code.
2. Extend Drifter from a *drift guard* into a *project truth system* without breaking its lightweight, cooperative-enforcement philosophy.
3. Add evidence and traceability primitives using **established methodology**: user stories, EARS requirements, Gherkin acceptance criteria, decision records, failure memory, and a repository-derived repo map.
4. Add boundary controls: blast-radius classification, change budgets, anti-churn stop rules, and scope-expansion blocking.
5. Add reconciliation: a "truth audit" that reports requirement/documentation/code/test/UAT alignment as a project health model.
6. **Leverage before build:** every workstream names the existing OSS it adopts or wraps, or justifies why none fits.
7. Preserve Drifter's existing guarantees: Python 3.10+, zero heavy runtime dependencies in core, `pip install`, cross-platform, all new behavior enforced by code rather than prompts. Leveraged tools and anything ML-based are optional extras, never core.

## 3. Current-State Coverage Assessment

Checklist items mapped to Drifter's current capabilities (per Drifter Wiki v1.3). **Gap** = no meaningful coverage; **Partial** = some mechanism exists but falls short; **Covered** = adequately addressed. The *Leverage* column names the existing OSS or standard each gap should be built on.

| # | Checklist item | Status | Leverage |
|---|---|---|---|
| 0 | Core principles (fact vs. assumption vs. claim) | Partial | Confidence labels (VERIFIED/INFERRED/ASSUMED/UNKNOWN) in record schemas |
| 1 | Machine-readable constitution | Partial | **Spec Kit `/constitution`** format alignment |
| 2 | Project knowledge graph | **Gap** | **aider repo map** (tree-sitter + SQLite cache + PageRank); Serena MCP as reference |
| 3 | Repository grounding (UNDERSTANDING before coding) | Partial | Repo map ranked rendering (W10/W11) |
| 4 | Hybrid evidence retrieval | **Gap** | Out of scope (future); repo map covers structural subset |
| 5 | Persistent memory (project/decision/failure/expiring) | **Gap** | **MADR** (ADRs); digest conventions already in Drifter |
| 6 | Requirements management + traceability | **Gap** | **EARS** notation, **Gherkin**, **StrictDoc**-style RTM, ISO 29148 |
| 7 | Agent task contract | Partial | **Backlog.md** frontmatter conventions (acceptance criteria, DoD, dependencies) |
| 8 | Blast-radius control | **Gap** | Repo map graph (W10); no direct OSS equivalent — bespoke but thin |
| 9 | Change budget | **Gap** | Bespoke (session-log counting); thin |
| 10 | Architecture protection | **Gap** | **import-linter** (Python layer contracts), **dependency-cruiser** (JS) — wrapped, not rewritten |
| 11 | Anti-churn system | **Gap** | Bespoke (session-log pattern detection); thin |
| 12 | Human comprehension gate | **Gap** | Protocol artifacts + W0b decision gates |
| 13 | Documentation synchronization | Covered | Existing Drifter checks |
| 14 | Truth audit (project health) | Partial | Aggregates existing check infrastructure |
| 15 | Security suite + AI data classification | Partial | **pip-audit, OSV-scanner, OpenSSF Scorecard** — wrapped |
| 16 | Dependency governance | **Gap** | **OpenSSF Scorecard**, Renovate/Dependabot metadata; justification record is bespoke (thin) |
| 17 | Copyright / license governance | **Gap** | **Scancode / licensee** — wrapped |
| 18 | Testing strategy (tests from requirements) | Partial | **Gherkin → pytest-bdd / behave** — acceptance criteria become executable |
| 19 | Database protection | **Gap** | Migration-framework conventions (Alembic/sqitch); approval logic bespoke (thin) |
| 20 | Observability | **Gap** | Acceptance-criteria category (NFR) + protocol artifact |
| 21 | Git discipline | Partial | **Conventional Commits** + existing `git_safety`/`git_commit_approval` |
| 22 | Multi-agent coordination | **Gap** | Bespoke file-ownership in session log (thin) |
| 23 | Agent handoff protocol | Partial | Backlog.md/Spec Kit artifact conventions |
| 24 | Confidence / uncertainty labeling | **Gap** | Confidence field in all record schemas |
| 25 | No silent scope expansion | Partial | **OpenSpec delta model** (ADDED/MODIFIED/REMOVED) as the scope-change record format |
| 26 | Requirement conflict detection | **Gap** | EARS lint + heuristic checks |
| 27 | Three-way drift detection | Partial | Extends existing doc/code checks to requirements axis |
| 28 | Project state machine | Partial | States gated by DoR/DoD/UAT records |
| 29 | Feature completeness score | **Gap** | Per-dimension truth audit (W12) |
| 30 | Technical debt ledger | **Gap** | Thin bespoke record type |
| 31 | Human skill protection | **Gap** | Protocol artifacts only |
| 32 | Production incident memory | **Gap** | Thin bespoke record type feeding regression requirements |
| 33 | Agent performance tracking | Partial | Extends `session-report` |
| 34 | Model independence | Covered | MCP server; MCP-first rule (§6) for all new capabilities |
| 35 | Golden rule enforcement | Partial | W0b gates + behavioral checks |

**Inception decision capture (added in v2):** no mechanism — in Drifter, the checklist, or any surveyed SDD tool — forces the initial human Q&A ("what tools are we using, is this the best fit, limitations, scaling, evidence, correct vs. easy and why?"). Spec Kit's `/clarify` interviews about *feature ambiguity*; nothing interviews about *decision quality*. This remains a genuine gap and Phase 0's justification.

## 4. Scope

### 4.0 Leverage-First Mandate (NEW in v3)

No workstream may implement bespoke logic where a maintained OSS project or published standard already solves the problem. Each workstream below declares its leverage. Permitted bespoke code is limited to: (a) thin glue/wrappers, (b) record schemas and checks that encode the checklist's governance semantics, (c) components with no existing equivalent (blast-radius gating, anti-churn, decision-drift). Every leveraged tool is an optional extra (`drifter[sec]`, `drifter[arch]`, etc.); core remains stdlib-only, and every check degrades gracefully (info-level "skipped, tool not installed") when its backend is absent.

**Positioning:** Drifter does not compete with Spec Kit, OpenSpec, or BMAD. Those tools author specs; Drifter makes authored truth *govern the code*. Interoperability with their artifact formats is an acceptance criterion (§6), not a nice-to-have.

### 4.1 Phase 0 — Human Decision Foundations

**Rationale:** drift checks are only as good as the truth they check against. Before any agent-facing machinery, the framework must extract and record the human's actual decisions — including the uncomfortable ones ("we chose X because it was easy, not because it was correct").

- **W0a. Project inception interview (`drifter init --interview`).** Structured, scripted Q&A at adoption time (re-runnable per major decision). Each answer stored as a typed record with a confidence label (VERIFIED / INFERRED / ASSUMED / UNKNOWN):
  - *Tooling:* languages, frameworks, databases, infrastructure, AI tools in use.
  - *Fitness:* is each the best fit for this use case? Alternatives evaluated and rejected?
  - *Limitations:* known limits of each choice (scale ceiling, license, maintenance risk, bus factor).
  - *Scaling:* what load/growth assumption does the choice hold under; what breaks first beyond it?
  - *Evidence:* has research/benchmarking been done, or is this assumed?
  - *Correct vs. easy:* every significant choice declares `chosen_because: correct | easy | familiar | deadline` plus `tradeoff_rationale`. "Easy" is legitimate — but auto-creates a tech-debt record (W4) with a review-by date, so convenience never becomes invisible permanent architecture.
  - Output: seeds `drifter-constitution.toml` (W1), generates initial MADR ADRs (W3), populates the dependency-governance baseline (W13). Unanswered questions are recorded as UNKNOWNs and surface in every truth audit (W12).
  - *Leverage:* question flow modeled on Spec Kit's `/clarify` interview pattern, but targeting decision quality rather than feature ambiguity.
- **W0b. Human decision gates.** Constitution declares boundaries requiring fresh human approval (architecture, schema, dependencies, security, destructive ops). Enforced via approval markers (extending `git_commit_approval`'s model) on any check bypass, constitution edit, or scope change; every override leaves a signed session-log entry. *Fresh, verbatim approval per decision — prior approval never rolls forward.*
- **W0c. Decision-drift check (`decision_drift`).** Flags code/config contradicting an ADR or constitution entry (e.g., constitution bans new state-management libraries; one appears in dependencies). Closes the loop: Phase 0 records the *why*, `drifter check` polices the *what*.
- **W0d. Check-profile split (carried from wiki §10.2).** `profile = "generic" | "drifter-self" | "strict"` in `drifter.toml`; the inception interview selects it. Fixes the #1 new-adopter trap before any new checks land.

### 4.2 Phase 1 — Truth Foundations (Requirements, Memory, Decisions)

- **W1. Machine-readable constitution (`drifter-constitution.toml`):** purpose, non-goals, tech stack, dependency policy, AI-agent policy, approval boundaries. **Format-aligned with Spec Kit's constitution concept** so a Spec Kit `constitution.md` can be imported/exported; agents may propose changes via PR but `drifter check` errors on unsigned edits. Seeded by W0a. *(§1)*
- **W2. Requirements registry — rebuilt on real BSA/PM methodology (revised in v3).** v2's flat TOML schema is replaced by a standards-based model:
  - **User stories** in canonical form: *As a [role], I want [capability], so that [outcome]* — with role/capability/outcome as separate lintable fields.
  - **Requirement typing:** functional requirements vs. non-functional requirements categorized per **ISO/IEC 25010** (performance, security, reliability, usability, maintainability, compatibility, portability, functional suitability).
  - **EARS notation** for system requirements (*When \<trigger\>, the system shall \<response\>*; Ubiquitous / Event-driven / State-driven / Unwanted-behavior / Optional patterns) — machine-lintable, the same notation Kiro uses.
  - **Gherkin acceptance criteria** (Given/When/Then) per story — executable through pytest-bdd/behave, making "tests generated from requirements, not implementation" literal (§18).
  - **MoSCoW priority** (Must/Should/Could/Won't) and **INVEST** validation (Independent, Negotiable, Valuable, Estimable, Small, Testable) per story.
  - **Traceability:** REQ → story → design → task → commit → files → tests, StrictDoc-style; powers "show me every requirement that isn't implemented" and "what requirements does this migration affect?"
  - New checks: `requirement_integrity` (schema + ID uniqueness), `requirement_quality` (EARS pattern lint, INVEST heuristics, story-form validation — NEW in v3), `requirement_traceability`, `requirement_conflict` (duplicate/contradiction heuristics). *(§6, §26)*
  - *Leverage:* EARS patterns, Gherkin grammar, ISO 29148 characteristics (unambiguous, verifiable, traceable...), StrictDoc as the RTM reference implementation.
- **W3. Decision & failure memory — MADR-based (revised in v3):** ADRs use the **MADR template** (compatible with adr-tools/log4brains) extended with two fields: `chosen_because` (from W0a) and `confidence`. `FAILED_APPROACH` records carry "do not retry unless" conditions. All memory has created / last-verified / confidence / superseded-by metadata; `memory_staleness` check. *(§5)*
- **W4. Technical debt ledger:** TD-ID records with owner and review-by date; `tech_debt_overdue` check; auto-populated when W0a records `chosen_because: easy`. *(§30)*

### 4.3 Phase 2 — Boundaries & Blast Radius

- **W5. Task contract extension — Backlog.md-aligned (revised in v3):** conductor tasks adopt Backlog.md-style frontmatter conventions (acceptance criteria, Definition of Done checklist, dependencies, milestones) plus Drifter-specific governance fields: `in_scope`, `out_of_scope`, `required_verification`, `max_files`, `max_lines`, `architectural_approval`, linked REQ-IDs. **Definition of Ready** gates activation (story has acceptance criteria, estimate, no unresolved UNKNOWN dependencies); **Definition of Done** gates completion via new `dod_gate` check (NEW in v3). Interop goal: a Backlog.md task file is a valid Drifter task record. *(§7, §9)*
- **W6. Change-budget enforcement:** session audit counts WRITEs per task; `budget_exceeded` check errors when limits are breached. *(§9)*
- **W7. Blast-radius classifier:** given a task's target files, compute affected dependents from the W10 repo-map graph, tests, and shared boundaries; classify LOW/MEDIUM/HIGH/CRITICAL; HIGH+ requires an approval marker (W0b). *(§8)*
- **W8. Anti-churn detection:** session-audit analysis flags ≥3 failed WRITE→TEST cycles on the same file; requires a root-cause entry before further writes pass `drifter check`. *(§11)*
- **W9. Scope-expansion stop rule — OpenSpec delta format (revised in v3):** discovered mid-task requirements are recorded as an **OpenSpec-style change delta** (proposal + ADDED/MODIFIED/REMOVED spec deltas) with impact classification and approval, instead of a bespoke SCOPE_CHANGE record. This makes Drifter scope changes directly interoperable with OpenSpec workflows. *(§25)*

### 4.4 Phase 3 — Knowledge & Reconciliation

- **W10. Repo map (aider's proven design):**
  - Tree-sitter tag extraction (definitions + references per file) via pip-installable wheels; Python fallback via stdlib `ast`.
  - **SQLite tag cache with mtime invalidation** (aider's tags-cache pattern) — incremental, offline, no language-server dependency.
  - **Graph ranking:** files as nodes, references as edges, PageRank-style importance personalized toward task-active files (aider uses a 50× boost) — answers "what depends on this file?" for W7 and upgrades `ghost_reference`.
  - **Token-budgeted rendering:** binary-search the map into a configurable budget, consistent with the ~9K-token pre-flight cost ceiling.
  - Explicitly *not* adopted from aider: auto-commit-per-edit (violates Drifter's git boundary rule) and editing backends (Drifter is a guard, not an editor). *(§2, §3)*
- **W11. UNDERSTANDING artifact:** `drifter preflight` emits a structured grounding template (repo-map-ranked relevant files, dependencies, existing behavior, unknowns) attached to the task record; the currently unused `--task` flag (wiki §3) is wired to actually scope this. *(§3)*
- **W12. Truth audit command (`drifter truth`):** aggregates requirements implemented/unverified, missing tests, stale docs, undocumented dependencies, stale memories, open tech debt, UAT status, and unanswered inception UNKNOWNs into a health report with per-dimension scores. *(§14, §27, §29)*
- **W13. Architecture & dependency governance — wrapped tools (revised in v3):** layer violations and forbidden-dependency checks are enforced by **wrapping import-linter** (Python; its "contracts" map 1:1 onto Drifter's `[boundaries]` manifest section) and **dependency-cruiser** (JS/TS), plus circular-dependency reports from both. New dependencies require a `DEPENDENCY_JUSTIFICATION` record (why needed, alternatives rejected, maintenance/license/vulnerability status via **OpenSSF Scorecard** data, existing-alternative check). Zero bespoke graph algorithms. *(§10, §16)*

### 4.5 Phase 4 — Security, Lifecycle & Multi-Agent

- **W14. Security suite — wrapped tools (revised in v3):** vulnerability scanning via **pip-audit**/**OSV-scanner**, license scanning via **Scancode/licensee**, dependency health via **OpenSSF Scorecard** — orchestrated as `drifter[sec]` extras, results normalized into Drifter issues. AI data-classification policy in the constitution with `restricted_path` rules preventing agents from reading SECRET-classified paths. Session-log attestation follows **in-toto/SLSA** provenance conventions rather than a bespoke signing format. *(§15, §17)*
- **W15. Lifecycle state machine:** conductor phases formalized into IDEA→PROPOSED→REQUIREMENTS→DESIGNED→APPROVED→IN DEVELOPMENT→IMPLEMENTED→TESTED→DOCUMENTED→**UAT**→ACCEPTED→PRODUCTION→MONITORED, with enforced transitions: DoR gates entry to IN DEVELOPMENT, DoD gates entry to DOCUMENTED, and **`uat_signoff`** (NEW check in v3) requires a recorded human UAT result — tester, date, Gherkin scenarios executed, pass/fail — before ACCEPTED. *(§28)*
- **W16. Database protection:** migration-file detection (Alembic/sqitch/Flyway conventions) requiring rollback-strategy frontmatter and approval markers before commit. *(§19)*
- **W17. Multi-agent coordination:** file-ownership registry in the session audit; `write_conflict` check warns/errors when two sessions WRITE the same file concurrently. *(§22)*
- **W18. Handoff & incident records:** structured `TASK_COMPLETE` handoff template; `INCIDENT-xxx` records with "why tests didn't catch it" feeding a regression-test requirement (as a Gherkin scenario, per W2). *(§23, §32)*
- **W19. Agent scorecards:** extend `session-report` into cross-session metrics (first-pass test success, human rejection rate, average blast radius, unnecessary-file-change ratio). Fix the known false positive ("test" substring counts as a test run — wiki §10.5). *(§33)*

### 4.6 Phase 5 (Optional) — Calibrated Decision Layer

- **W20. `drifter[decide]` — optional Laya-based decision plugin.** [Laya](https://huggingface.co/convaiinnovations/laya) is a local, non-autoregressive decision model: given a state plus typed questions (`choice`/`score`/`noul`), it returns calibrated probabilities in a single ~33 ms forward pass — no text generation, nothing to hallucinate. Candidate uses, all *advisory* (human gate W0b stays authoritative):
  - Blast-radius classification as a `score` question over the task record + repo-map summary (augments W7 on ambiguous cases).
  - "Does this change require human approval?" as a `noul` gate with confidence threshold — a local, auditable decision instead of an external LLM call.
  - Drift-issue severity triage when heuristics disagree.
  - **Hard constraints:** optional extra only; ~800 MB weights and 512-token question budget documented; every model decision logged with confidence; low-confidence decisions escalate to humans.
  - **Known limitation (model card):** base checkpoints are near chance zero-shot on typed decisions (0.362 vs 0.461 majority baseline); value comes from fine-tuning.
  - **Training data: Drifter's own logs, not external datasets.** Session audits, archive records, and conductor history already contain labeled outcomes (churned tasks, rejected changes, wrong blast-radius calls). W20 includes an exporter turning this history into a fine-tuning set. External datasets evaluated and **rejected**: `warrencain/Business_Scenario_Knowledge_Dataset` (CEO strategy chat, off-domain), `Seraphnetai/db_bsa_instruct` (mixed finance-instruction data, noisy).

### 4.7 Out of Scope (this program)

- Full semantic/vector RAG context engine (checklist §4) — future exploration; the repo map provides the structural subset.
- Spec/plan/task **authoring** — deliberately left to Spec Kit / OpenSpec / BMAD; Drifter consumes and enforces their artifacts (§4.0 positioning).
- Cloud/hosted services, dashboards, SaaS — Drifter remains a local, pip-installable CLI. (Backlog.md's board/web UI can be used alongside for visualization.)
- Automatic context injection into agent sessions (documented non-goal).
- Human-comprehension and skill-retention gates (§12, §31) beyond decision records and approval gates — remainder delivered as protocol templates.

## 5. Deliverables

| Deliverable | Description | Phase | Key leverage |
|---|---|---|---|
| D0 | Inception interview CLI, decision-gate config, `decision_drift` check, check profiles | 0 | Spec Kit clarify-pattern |
| D1 | Constitution schema + validation + Spec Kit import/export | 1 | Spec Kit constitution |
| D2 | Requirements registry: user stories, EARS, Gherkin, MoSCoW, INVEST, RTM + 4 checks | 1 | EARS, Gherkin, ISO 25010/29148, StrictDoc-style RTM |
| D3 | MADR ADRs / failure-memory / tech-debt records + staleness checks | 1 | MADR, adr-tools |
| D4 | Task contract (Backlog.md-aligned) + DoR/DoD gates + budget enforcement + blast-radius classifier | 2 | Backlog.md format |
| D5 | Anti-churn stop rule + OpenSpec-delta scope-change records | 2 | OpenSpec delta model |
| D6 | Repo map (tree-sitter + SQLite cache + ranking + token budgeting) + UNDERSTANDING artifact | 3 | aider repo map |
| D7 | `drifter truth` audit report | 3 | — |
| D8 | Architecture & dependency governance via wrapped linters + justification records | 3 | import-linter, dependency-cruiser, OpenSSF Scorecard |
| D9 | Security/license suite, in-toto-style attestation, lifecycle + UAT gates, DB protection, multi-agent checks | 4 | pip-audit, OSV, Scancode, in-toto/SLSA |
| D10 | Handoff/incident templates + agent scorecards | 4 | — |
| D11 | `drifter[decide]` plugin + session-log training-data exporter | 5 (optional) | Laya |
| D12 | Updated docs: methodology, adoption guide, rules reference, README, AGENTS.md | All | — |
| D13 | Test suite covering all new checks (Drifter's own `test_coverage` rule applies) | All | — |

Each new check ships with: registry entry, severity, `ignore_paths`/`ignore_patterns` support, manifest declaration (`manifest_sync`, `config_sync`, `claim_sync`), documentation — **and an MCP tool** (MCP-first rule, §6).

## 6. Acceptance Criteria

1. Every new capability is enforced by a check, a CLI command, or a signed artifact — never by prompt text alone.
2. **MCP-first rule:** every new check and CLI capability is exposed through the MCP server plugin in the same release. Prerequisite fix: declare `fastmcp` in `pyproject.toml` as `[project.optional-dependencies] mcp = ["fastmcp"]`.
3. **Leverage-first rule (NEW in v3):** no PR introduces bespoke logic duplicating a maintained OSS capability listed in §3/§4 without an explicit ADR justifying why the existing tool doesn't fit.
4. **Interoperability (NEW in v3):** Drifter must (a) import a Spec Kit constitution and per-feature `spec.md`/`tasks.md` as constitution/tasks, (b) accept an OpenSpec change delta as a scope-change record, (c) accept a Backlog.md task file as a valid task record, (d) accept a MADR file as a valid ADR.
5. `drifter check` runs clean on the Drifter repository itself with all new checks enabled.
6. All new checks suppressible per-path/per-pattern and documented in `docs/rules-reference.md`; checks with missing optional backends degrade to info-level "skipped," never silent pass (wiki §10.2 pattern).
7. Numerical claims in docs match manifest values (`claim_sync` passes).
8. No new **core** runtime dependencies beyond stdlib; leveraged tools (tree-sitter, import-linter, pip-audit, laya…) are extras.
9. Backward compatibility: existing `drifter.toml` and conductor files continue to load; migrations automatic or documented.
10. Pre-flight token cost under ~15K input tokens; repo-map rendering is token-budgeted.
11. **Human-decision completeness:** a project is not constitution-complete until every inception question has an answer or an explicit UNKNOWN; unsigned constitution/ADR edits fail `drifter check`.
12. **Requirements quality (NEW in v3):** 100% of stories pass `requirement_quality` (story form, EARS lint, INVEST heuristics); every Must-have story has ≥1 Gherkin scenario; no feature reaches ACCEPTED without a `uat_signoff` record.
13. All ML-assisted decisions (W20) advisory, confidence-logged, subordinate to human gates; the system is fully functional with the plugin absent.

## 7. Assumptions & Constraints

- Drifter's **cooperative enforcement model** is retained; mandatory gating via `drifter install-hook` and CI.
- Repo map (W10) works offline; tree-sitter wheels preferred, stdlib `ast` Python fallback, warn-level degradation for unsupported languages.
- Multi-agent coordination (W17) assumes a shared filesystem/audit log; network coordination out of scope.
- Wiki hygiene items (§10: unwired reporters, unapplied severity overrides, `conductor next` stub, template packaging via `importlib.resources`, stale URLs, missing ruff/mypy config) are folded into the phases where they touch new code; the profile split ships in Phase 0 (W0d).
- Leveraged OSS is evaluated for license compatibility (MIT/Apache-2.0 preferred — Drifter is dual MIT/Apache) and maintenance health (bus factor, release cadence) before adoption; each adoption is recorded as an ADR — the framework eats its own cooking.
- Timeline and resourcing indicative; each phase independently shippable.

## 8. Suggested Sequencing & Effort

| Phase | Workstreams | Indicative effort | Rationale for order |
|---|---|---|---|
| 0 — Human Decision Foundations | W0a–W0d | 2–3 weeks | Everything else checks drift *against* decisions; without recorded decisions there is no truth to check against. Also fixes the #1 adoption trap (profiles) |
| 1 — Truth Foundations | W1–W4 | 3–4 weeks | Requirements/memory records are prerequisites for traceability, truth audit, DoR/DoD; seeded by Phase 0 |
| 2 — Boundaries & Blast Radius | W5–W9 | 3–4 weeks | Highest immediate risk reduction; builds on Phase 1 records |
| 3 — Knowledge & Reconciliation | W10–W13 | 4–5 weeks | Repo map is the heaviest engineering; unlocks blast-radius precision and truth audit. Wrapping import-linter/dependency-cruiser keeps W13 thin |
| 4 — Security, Lifecycle & Multi-Agent | W14–W19 | 3–4 weeks | Wrapping pip-audit/OSV/Scancode keeps W14 thin; lifecycle gates build on W2/W5 records |
| 5 — Calibrated Decision Layer (optional) | W20 | 2–3 weeks | Only after enough session history exists to fine-tune on; near-chance without project data |

Leverage-first materially shrinks v2 estimates for W13 and W14 (wrappers instead of engines) and de-risks W2 (proven formats instead of a novel schema).

## 9. Risks

| Risk | Mitigation |
|---|---|
| Check-count growth erodes usability (35 → 60+ checks) | Profiles (`generic`, `drifter-self`, `strict`) selected by the inception interview |
| Leveraged tools become unmaintained | Each adoption recorded as an ADR with alternatives noted; wrappers isolate swap cost; checks degrade gracefully when backend absent |
| Methodology overhead (EARS/Gherkin/UAT) too heavy for small projects | `generic` profile enables only integrity/traceability; `strict` profile enables quality/UAT gates; the interview makes this an explicit choice |
| Repo-map accuracy across languages | Tree-sitter wheels cover the mainstream; unsupported languages warn, never error |
| Ceremony fatigue | Auto-generate records from CLI; interview resumable; UNKNOWN is a valid recorded answer |
| Enforcement rigidity vs. "cooperative guard" positioning | Every gate has a documented override leaving a signed audit entry (W0b) |
| W20 confident-but-wrong classifications | Advisory-only, confidence thresholds, fine-tune on own logs first, core never depends on it |
| Inception answers go stale | `decision_drift` + `memory_staleness` surface contradictions; truth audit reports stale/UNKNOWN counts |
| SDD tooling churn (Spec Kit/OpenSpec formats evolve) | Interop layer isolated behind importers; format versions pinned per ADR |

## 10. Success Measures

- 100% of significant tooling/architecture choices have a MADR ADR with `chosen_because` and confidence label; zero unsigned constitution edits pass CI.
- 100% of Must-have requirements carry Gherkin acceptance criteria; ≥90% have full REQ→code→test traceability; zero features reach ACCEPTED without UAT sign-off.
- Truth audit in CI on every PR; drift errors and unanswered UNKNOWNs trending down.
- Fewer `read_before_write` / `test_after_write` violations per session over time.
- Zero new mandatory core runtime dependencies; all governance reachable via MCP by ≥2 independent agent harnesses.
- Every `chosen_because: easy` decision has a live tech-debt record with a review-by date.
- Interop suite green: Spec Kit, OpenSpec, Backlog.md, and MADR artifacts import cleanly in CI fixtures.
