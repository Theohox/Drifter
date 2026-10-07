---
title: SOW v3 Critique — Drifter Framework Improvement Program
type: reference
version: "1.0"
status: draft
phase: "3"
created: '2026-10-06T20:40:00Z'
updated: '2026-10-07T12:00:00Z'
---

# SOW v3 Critique — Drifter Framework Improvement Program

Review of `docs/Drifter_SOWchanges.md` (SOW v3, 260 lines), produced by 13 parallel reviewers:
7 repo-side feasibility reviewers (findings verified against source, cited as `file:line`)
and 6 web-verification reviewers (external claims checked against primary sources, cited by URL).
Review date: 2026-10-06.

**Overall verdict:** The SOW's skeleton is genuinely strong — changelog coherence, complete
workstream-to-deliverable mapping, a sound leverage-first philosophy, and mostly accurate
external claims. But it is **not ready for adoption as written**. Nine blocker-class findings
sit on the critical path, including one live bug in shipping code that the SOW's own Phase 0
depends on, and two acceptance criteria (AC1/AC11, AC10) that cannot be tested because the
concepts they invoke ("signed artifact", "token cost") are undefined.

Finding counts: **9 blockers**, **~25 significant**, **~20 minor**. Every external tool named
in the leverage matrix exists; the errors are in the details (licenses, distribution formats,
one obsolete ISO standard, and one falsifiable competitive-positioning sentence).

---

## 1. Executive Summary — Verdict per Workstream

| Workstream | Verdict | One-line reason |
|---|---|---|
| W0a inception interview | Go, with amendments | Needs non-interactive `--answers` mode (MCP-first conflict) + Phase 1 schemas pulled forward |
| W0b decision gates | Go, with amendments | It is a new subsystem (approval records, grant path, suppression syntax), not an "extension" |
| W0c `decision_drift` | **Rescope** | Free-text ADR contradiction detection is infeasible; only declarative policy-vs-manifest checks are buildable |
| W0d check profiles | **Blocked by prerequisite** | Config `_merge` replaces check lists wholesale; profiles cannot work until that is fixed |
| W1 constitution | Go, with amendments | Signing mechanism and CI verification undefined; precedence vs `dangerous_patterns.toml` unstated |
| W2 requirements registry | **Split + rescope** | `requirement_conflict` overpromises; Phase 1 is a ~2x underestimate driven by W2 |
| W3 MADR memory | Go, with amendments | ADR storage location collides with every existing doc validator; adr-tools claim is wrong |
| W4 tech-debt ledger | Go | Genuinely thin; needs a taxonomy boundary vs blocked tasks and digest PENDINGs |
| W5 task contract | **Redesign** | Full conductor storage migration, not an "extension"; Backlog.md tooling strips unknown frontmatter keys |
| W6 change budget | **Blocked** | Session log records no task ID, no line counts, no session boundaries |
| W7 blast radius | **Resequence or descope** | Declared dependency on W10 (Phase 3) while sitting in Phase 2 |
| W8 anti-churn | **Blocked** | Log records no test exit codes; depends on a W19 fix sequenced two phases later |
| W9 scope-expansion deltas | Go, with amendments | "Stop rule" overpromises; it is post-hoc detection + recording |
| W10 repo map | Go, with amendments | aider design verified accurate; name the tree-sitter package, add runtime budget, drop the `ghost_reference` claim |
| W11 UNDERSTANDING | Go, with amendments | Persistence mechanism ("attached to the task record") does not exist |
| W12 `truth` command | Specify the contract | Does not fit the `Report` dataclass; public-API decision is unstated |
| W13 arch/dep governance | Split | pip extras can only deliver import-linter; dependency-cruiser is Node; "1:1 mapping" overstated |
| W14 security suite | Split | in-toto/SLSA is a category error for the session log; OSV-scanner/Scorecard/licensee can't be pip extras |
| W15 lifecycle states | Clarify + harden first | Conflates project-wide phase with per-feature lifecycle; conductor parser cannot enforce transitions today |
| W16 DB protection | Go, with amendments | Uniform "rollback frontmatter" contradicts Alembic/Flyway/sqitch realities |
| W17 multi-agent | **Blocked** | Log has no session identity; pid is not a session (47 WRITEs, ~47 pids in the live log) |
| W18 handoff/incident | Go | Thin templates; no issues found |
| W19 scorecards | **Blocked** | 3 of 4 proposed metrics have no data source in the current log |
| W20 Laya plugin | Go (optional), with amendments | Headline numbers verified; but "logs contain labeled outcomes" is false, and the flagship `noul` use hits a documented model defect |

---

## 2. Blockers (must fix before adoption)

### B1. Config merge silently disables all unlisted checks — live bug, and W0d depends on it

`Config._merge` replaces lists wholesale; only dicts deep-merge
(`src/drifter/config.py:212-220`). `run_checks` only runs checks present in `config.checks`
(`src/drifter/drift_guard.py:49-53`). Verified experimentally: a `drifter.toml` with one
`[[drifter.checks]]` entry runs exactly one check — the other 34 vanish. Consequences:

- The wiki's own adoption-playbook starter config (`docs/wiki.md:511-570`), which claims
  unlisted checks "inherit DEFAULT_CONFIG = enabled", today produces a guard that checks
  **nothing** and reports score 100 — a silent full pass, the exact failure mode Drifter
  exists to catch.
- W0d profiles are named check lists riding on exactly this merge path. Profiles cannot
  work until merge semantics become per-name overlay.

**Amend:** Add an explicit Phase 0 prerequisite: "fix `_merge` to overlay `checks` entries
per `name`; regression test; fix wiki §11 starter config." Add an acceptance criterion:
partial check config leaves unlisted checks at default enablement.

### B2. "Signed artifact" is undefined — AC1, AC11, and W1 are unimplementable as written

The only signing mechanism that exists is HMAC-SHA256 over session-log entries, with a
per-repo secret at `.drifter/.session_secret` (gitignored). No file-signing scheme for
TOML/markdown is specified anywhere: who signs, what key, what canonical form is hashed.
Worse, a signature made with a gitignored local secret is unverifiable on a fresh CI clone,
so AC11 ("unsigned constitution/ADR edits fail `drifter check`") and AC5 (clean run in CI)
cannot both hold. Related honesty issue: HMAC proves integrity, not human authorship — the
secret is agent-readable, so any "signed approval" can be minted by the agent itself. The
SOW's W0b language should not imply otherwise.

**Amend:** Define the trust mechanism explicitly — e.g. approval markers in the signed log
(extending the `git_commit_approval` marker model) plus a committed hash verified in CI
against a human-approved `[APPROVED BY]` commit marker. Add the caveat: "signatures attest
integrity in a cooperative model; human authorship is not cryptographically proven — use
pre-commit hooks/CI for mandatory gating."

### B3. Token budgets are contradictory and unmeasurable — AC10 is untestable

W10 cites a "~9K-token pre-flight cost ceiling" (line 136); AC10 says "under ~15K input
tokens" (line 201). Two different ceilings, no source for either, and **nothing in Drifter
measures tokens** — no tokenizer dependency, no instrumentation. The ~9K figure traces to a
hand-counted character table in `docs/adoption-guide.md:218-248`. W11 also adds repo-map
output *on top of* the existing docs, so the 9K "ceiling" is exceeded by construction.

**Amend:** Pick one number, define the measurement (tokenizer or an explicit chars/4
estimate, fixture repo, harness — e.g. a `drifter measure-context` command), record the
current baseline, or demote AC10 to a design goal.

### B4. Session-log schema cannot support W6, W8, W17, W19, or W20

The log entry format is `[timestamp|pid|action|target|hmac16]`
(`src/drifter/session_logger.py:69-71`). Against the SOW:

- **W6 "counts WRITEs per task":** no task ID is logged; conductor transitions are never
  logged. No window in the log corresponds to "a task."
- **W6 `max_lines`:** no line/byte counts recorded anywhere.
- **W8 "≥3 failed WRITE→TEST cycles":** SHELL entries record the command, never its exit
  code. Passing and failing pytest runs are indistinguishable.
- **W17 `write_conflict`:** pid is not a session ID — every `drifter log` CLI call is a
  fresh process (verified: 47 WRITE entries, ~47 distinct pids in the live log). No
  SESSION_START/END markers exist, so "concurrently" is undefined.
- **W19 scorecards:** "human rejection rate" and "first-pass test success" have no data
  source; no rejection or result events exist.
- **W20 training data:** the claim "logs already contain labeled outcomes (churned tasks,
  rejected changes, wrong blast-radius calls)" is **false** — none of those features exist
  yet, and no labels of any kind are recorded. The live log is 126 lines; cross-project
  pooling collides with per-repo HMAC secrets and gitignored `.drifter/`.

Forward-compatibility trap: `read_entries` does `body.split("|", 3)`
(`session_logger.py:99`), so naively appending fields is silently swallowed by old readers.
A v2 schema needs an explicit version marker.

**Amend:** Add a dedicated early workstream — **session-log schema v2** (task_id,
session_id, SESSION_START/END, TEST_RESULT, HUMAN_FEEDBACK action types, versioned reader
migration) — landing in Phase 1. It unblocks W6, W8, W9 detection, W17, W19, and W20's
data story simultaneously. Until then, descope W6 to `max_files` approximation, redefine
W8 as "repeated WRITE→test→WRITE cycles" (implied failure), and gate W17/W19/W20 on v2.

### B5. W7 (Phase 2) depends on W10 (Phase 3) — sequencing contradiction

W7 computes "affected dependents from the W10 repo-map graph" (line 126) but ships a phase
earlier. §8's rationale tacitly concedes this ("Phase 3 … unlocks blast-radius precision")
without defining the degraded form, violating "each phase independently shippable."

**Amend:** Define W7a (Phase 2): Python-only stdlib-`ast` import graph + test-name
heuristics, LOW/MEDIUM/HIGH only; W7b (Phase 3): swap the graph backend to the repo map
behind an interface. Or move W7 to Phase 3. Also define "shared boundaries" or drop it.

### B6. in-toto/SLSA attestation is a category error and contradicts AC9

W14 says attestation "follows in-toto/SLSA provenance conventions **rather than** a bespoke
signing format." Three problems: (1) SLSA provenance describes *build artifacts*; a
behavioral audit log has no build — what applies is an in-toto ITE-6 Statement with a
Drifter-defined predicateType in a DSSE envelope, not "SLSA." (2) The current HMAC log
*is* the bespoke format being dismissed; replacing it breaks AC9 backward compatibility
(which never mentions the session log) and every behavioral check that parses it.
(3) in-toto assumes asymmetric keys; HMAC inside DSSE adds format complexity with zero
verifiability gain — this is an underspecified cryptographic redesign, not a format swap.

**Amend:** Keep the HMAC log. Add an optional attestation-export extra that emits a session
slice as an in-toto Statement/DSSE envelope for CI consumption. Drop "SLSA." Extend AC9 to
name the session log and its migration path.

### B7. W0c `decision_drift` is infeasible in its stated general form

"Flags code/config contradicting an ADR or constitution entry." ADRs are free-text
markdown; even MADR's structured fields encode no machine-checkable constraints on code.
The SOW's own worked example (constitution bans a dependency; one appears) is tractable
only because it reduces to declarative policy vs. a parsed manifest.

**Amend:** Rescope to "checks declarative policy fields in `drifter-constitution.toml`
(dependency allow/deny, restricted paths, banned commands) against parsed project manifests."
Free-text contradiction detection becomes an explicit non-goal, or ADRs carry an optional
machine-readable `enforces:` block the check consumes.

### B8. `requirement_conflict` overpromises contradiction detection

Duplicate detection is feasible (stdlib `difflib`). *Contradiction* detection between
natural-language requirements is an NLI problem; keyword heuristics yield near-zero recall
or a false-positive farm (the repo already has that cautionary tale: `credential_leak`'s
bare 40-char base64 pattern). A real solution needs ML, contradicting Objective 7 and AC1.

**Amend:** Rescope to `requirement_duplicate` (similarity + same-ID-different-text +
mutually exclusive modality heuristics, e.g. `shall` vs `shall not` over the same
subject/trigger). Move semantic contradiction to an explicitly advisory optional extra.

### B9. W20's flagship use case targets a documented model defect

Verified against the Laya model card: the SOW's headline numbers check out (non-autoregressive,
`choice`/`score`/`noul`, 0.362 vs 0.461 baseline, ~808 MB English checkpoint, Apache-2.0,
actively maintained). But:

- W20 proposes "does this change require human approval?" as a `noul` gate — and the card's
  Honest Limits warn that **`noul` can follow its option labels instead of the state, most
  strongly on the English checkpoint** (issue #156); recommended workaround is a two-option
  `choice` with neutral keys.
- "Calibrated probabilities" overclaims: the model ships over-confident (ECE 0.466 → 0.081
  only after per-question-type temperature fitting on your own data). The SOW's confidence
  thresholds are unsound until that fitting step exists.
- `drifter[decide]` pulls torch + transformers + huggingface_hub (~2.5+ GB) — omitted from
  the "lightweight" framing; an ONNX path (`laya[onnx]`) exists and is not considered.
- "~33 ms" is T4 GPU (CPU: 193–464 ms); "512-token question budget" conflates total
  context with the 192-token option-head budget (and the typed-decisions checkpoint, the
  fine-tune target, uses 1024).
- Combined with B4/B9's false training-data claim, W20 needs a minimum-data gate.

**Amend:** Approval gates as two-option `choice`; gate on `confidence`, never
`act_probability` (card: "no usable signal", AUROC 0.30); add a calibration-fitting step;
document the real runtime footprint; reword the data rationale to "weak labels synthesized
from behavioral-check outcomes plus log-v2 outcome events"; add "do not fine-tune until ≥N
labeled decisions exist."

---

## 3. Significant Findings by Phase

### Phase 0

- **F3-phase-coupling:** Phase 0's outputs (seed constitution, generate ADRs, create
  tech-debt records) all depend on Phase 1 schemas. Pull constitution/ADR/tech-debt schema
  v1 definitions into Phase 0, or Phase 0 ships records Phase 1 will redefine.
- **W0b is a new subsystem:** the existing model is retroactive detection only
  (`git_commit_approval` scans commits after the fact). There is no way for a human to
  *supply* an approval — no grant CLI, no approval store, no per-run check-suppression
  syntax. W0b must build the whole grant/record/verify pipeline.
- **W0a vs MCP-first:** an interactive stdin interview cannot be an MCP tool, yet AC2
  requires every new capability via MCP. Specify `--answers FILE` / resumable answers
  records; the MCP tool wraps the non-interactive path.
- **`strict` profile is empty in Phase 0:** its member checks (`requirement_quality`,
  `uat_signoff`, `dod_gate`) are Phase 1/2/4. Ship `generic | drifter-self` first, or
  define `strict` as explicitly forward-looking. Profile membership should be enumerated
  in the SOW (the 12 self-specific checks are listed in `docs/wiki.md` §10-11).
- **Severity overrides are inert:** `drift_guard.py:49-53` consults only `enabled`;
  configured `severity` never remaps issues. At 60+ checks this is the primary tuning
  lever after profiles. Fix is ~10 lines; name it as a Phase 0 task.

### Phase 1

- **Constitution vs `dangerous_patterns.toml`:** two sources of truth for approval
  boundaries. Define precedence, or make `dangerous_patterns.toml` a rendered projection
  of the constitution with a sync check.
- **Spec Kit constitution "import" overstates feasibility:** Spec Kit's constitution is
  free-form prose markdown with no schema
  ([spec-kit](https://github.com/github/spec-kit)). Import into typed TOML is an
  agent-assisted mapping, not a mechanical converter. Export (TOML→prose) is feasible.
  Downgrade AC4(a) accordingly.
- **ADR storage collides with every existing validator:** no `decision` doc type exists
  (`src/drifter/_doc_validate.py:12-21`), so stock MADR files fail `drifter validate`;
  `docs/archive/` triggers `archive_integrity` naming rules; `docs/digests/` triggers
  `digest_staleness`. Specify `docs/decisions/`, add `decision`/`requirement`/`tech-debt`
  to `VALID_TYPES` (a documented AC9 migration), extend MADR frontmatter as a superset.
- **INVEST "validation":** only Small and Testable are machine-checkable; I/N/V are human
  judgment. Rename to "INVEST heuristics (S/T enforced; I/N/V self-declared, surfaced in
  truth audit)."
- **Traceability degrades silently:** REQ→commit→files needs REQ-IDs in commit messages —
  a convention nothing enforces. Make `requirement_traceability` emit explicit info issues
  when git/ID data is absent; add the commit-message convention as a Phase 1 checked item.
- **Phase 1 effort is a ~2x underestimate:** W2 alone (schema, EARS linter, Gherkin,
  MoSCoW/INVEST, 7-link RTM, 4 checks + tests + MCP tools + Spec Kit importers + dogfooding)
  is 3-4 weeks by itself. Split: W1+W3+W4 (2-3 weeks), then W2 as its own phase.

### Phase 2

- **W5 is a storage-model rewrite:** conductor is one file with five fixed tables edited by
  regex/line surgery (`src/drifter/conductor.py:52-246`); Backlog.md is a directory of
  per-task files. Migration blast radius: all 6 Conductor methods, 3 project checks,
  pre_flight steps 3/5, templates, the canonical conductor doc, and the doc-type system.
  Backlog.md has no exactly-one-active-task concept, no phase tracking, no Drift Score
  History — a hybrid design is the only viable shape. AC9 requires a migrator that appears
  in no deliverable; add `drifter conductor migrate` to D4.
- **Backlog.md strips unknown frontmatter keys on edit** (verified against upstream
  `serializeTask`): W5's governance fields (`in_scope`, `max_files`, …) would be deleted
  the moment Backlog.md's CLI/MCP/Web UI touches the file. Rescope interop to one-way
  import, or move governance metadata into a managed-unknown-safe body section
  (e.g. `## Governance`), and require a round-trip fixture test. The §4.7 "use alongside
  for visualization" parenthetical is unsafe as written. (Also: Backlog.md acceptance
  criteria and DoD are *body sections*, not frontmatter — the SOW mislocates them.)
- **W8 depends on the W19 test-detection fix** (the `"test" in target` substring false
  positive, `src/drifter/cli.py:419`) sequenced two phases later. Move the fix into W8 as
  a shared `is_test_run()` classifier.
- **W9 "stop rule" overpromises:** detection is post-hoc via W6 counting; rename to
  "scope-expansion detection and delta recording"; specify storage path and declare the
  W0b/W6 dependencies.
- **Phase 2 effort optimistic:** it contains a conductor migration + log schema v2 + 4 new
  checks + W9 — rivals Phase 3's "heaviest engineering" yet is estimated a week shorter.
  Move log v2 to Phase 1 (it unblocks everything) or raise to 4-5 weeks.

### Phase 3

- **Cache lifecycle vs the parallel engine:** `run_checks` uses
  `ThreadPoolExecutor(max_workers=4)` (`src/drifter/drift_guard.py:56`); lazy SQLite cache
  builds would race across threads, and stdlib `sqlite3` connections are not shareable.
  Build/refresh the tags cache synchronously before the parallel phase (or via a separate
  a separate map command); checks get a read-only snapshot. Add a runtime budget
  (e.g. "warm-cache check overhead < 1s; cold build < 30s on 100k LOC") — the SOW has
  token budgets but no runtime budget, and `drifter check` runs in the pre-commit hook
  *and* inside preflight step 4.
- **W10 "upgrades `ghost_reference`" is wrong:** that check validates `` `drifter <cmd>` ``
  mentions in markdown against the capability manifest
  (`src/drifter/checks/ghost_reference.py:44-46`). A code graph has no bearing on it.
  Delete the claim or name a real consumer (`dead_code`, cross-file reference checks).
- **Name the tree-sitter dependency:** `tree-sitter-languages` is unmaintained since
  2024-02 (per its own README); the successor is `tree-sitter-language-pack` (MIT,
  cp310-abi3 wheels, ≥3.10, actively maintained — note its repo recently transferred
  owners, a bus-factor note for the adoption ADR). Pin a compatible
  tree-sitter/language-pack pair; the `Query.captures` API moved in 0.24. Also note
  aider's cache is the `diskcache` package — Drifter should implement with stdlib
  `sqlite3` and budget for reimplementing its error handling. W10 is
  bespoke-modeled-on-aider and should be declared under §4.0(c).
- **Aider mechanism precision:** the "50× boost" is an *edge-weight multiplier* on edges
  whose referencer is a chat file; personalization is a separate restart-probability
  vector (aider's `repomap.py`, `get_ranked_tags`). Aider license is Apache-2.0 — design
  adoption is license-safe. **Serena's application is GPL-3.0-or-later** (only its
  SolidLSP component is MIT) — fine as design reading, but no Serena code may be ported;
  flag this preemptively per the SOW's own license-evaluation rule.
- **W13 split:** pip extras deliver import-linter (BSD-2-Clause, ≥3.10 — but a
  single-maintainer project; record bus factor) and pip-audit (clean); dependency-cruiser
  is Node, OSV-scanner is Go, Scorecard is Go — none expressible as pip extras. Split into
  "pip extras" vs "external binaries" (PATH detection, min versions, documented as outside
  pip management). The "`[boundaries]` maps 1:1 onto import-linter contracts" claim is
  doubly inaccurate: `[boundaries]` was **deleted from `drifter-manifest.toml`** (zero code
  consumers — W13 would reintroduce it as its first consumer), and `may_import` whitelists need
  translation to forbidden-contract complements. Specify that Drifter *generates* the
  import-linter config and `config_sync` verifies parity.
- **OpenSSF Scorecard constraints:** the REST API only covers repos with published
  results — precisely not the obscure new dependencies a justification gate scrutinizes;
  local runs need a `GITHUB_TOKEN`; everything needs network. AC6 contemplates only
  "backend not installed" — add "network unavailable" and "no data for this artifact" as
  distinct info-level outcomes, never silent pass.
- **`truth` command contract:** per-dimension health cannot be expressed in the `Report`
  dataclass (single penalty score, capped weights). Specify a new `TruthReport` and the
  command's relationship to `drifter check`.
- **Extras policy missing:** enumerate the full extras set (`mcp`, `map`, `arch`, `sec`,
  `decide`); state that extra-backed checks default to disabled in the `generic` profile
  and auto-enable (info-degraded) when their backend is importable.

### Phase 4 + 5

- **W15 conflates two "phase" concepts:** the conductor's phase is a project-wide free-form
  marker; the 13-state list is a per-feature lifecycle. State explicitly that the state
  machine is per-task, orthogonal to project phase — and note conductor's regex parser
  cannot enforce transitions today (parser hardening is a prerequisite, already flagged in
  `docs/wiki.md` §10.3/§10.7).
- **W16 per-tool reality:** Alembic's rollback signal is a non-empty `downgrade()` body
  (AST-detectable, better than frontmatter); Flyway Community has no undo at all (paid
  feature) — "rollback-strategy frontmatter" is near-meaningless there; only sqitch
  natively generates revert scripts. Reword per tool; add `migration_paths` config.
- **W14 scanning is the thin part; attestation is not:** see B6. Also `restricted_path`
  read-prevention does not exist — `ToolInterceptor.before_read` is log-only
  (`src/drifter/plugin_api.py:25-28`); it must be built, not configured.
- **`uat_signoff` honesty:** like all approval markers, it is spoofable by the agent —
  consistent with the cooperative model, but say so in one sentence.
- **Phase 4 effort not credible:** W15 needs conductor hardening, W17/W19 need log v2,
  W14 needs scoping down. Split 4a (W14 scanning + W16, genuinely thin) / 4b (log v2 →
  W17/W19, conductor hardening → W15), or raise to 5-6 weeks.

### Cross-cutting (acceptance criteria, risks, docs)

- **Per-check self-hosting toil:** AC5 means every new check touches ~10 files (registry,
  DEFAULT_CONFIG, `drifter.toml` stanzas enforced error-level by `config_sync`, template,
  manifest `[checks]` enforced error-level by `manifest_sync`, architecture.md bullets,
  AGENTS.md tables, README claims, rules-reference, MCP tool, test file). At 60+ checks
  this linear tax grows the very drift the tool polices. Add a "check-registration
  single-sourcing" workstream (wiki §10.4 already recommends it) and define what "clean"
  means in AC5 (error-zero vs warn-zero).
- **Dogfooding ceremony tax:** AC5 × AC11 × AC12 require the Drifter repo itself to
  maintain a constitution, 100%-quality stories, Gherkin per Must story, and UAT records —
  permanent process overhead absent from §8 estimates.
- **Score saturation at 60+ checks:** the formula caps at `min(errors,10)*10 +
  min(warns,25)*2` (`drift_guard.py:91-93`); score loses discrimination exactly when the
  count doubles. Revisit weighting when the count roughly doubles.
- **`tree_integrity` vs record proliferation:** the program generates ADR/REQ/TD/INCIDENT
  files and a SQLite cache faster than a per-file manifest can track; the manifest needs
  glob/directory declarations.
- **Docs upkeep:** `docs/wiki.md` hardcodes "35 built-in checks" and is not covered by
  `claim_sync` or D12; `rules-reference.md` has `max_lines = 320` — documenting 60+ checks
  in 320 lines is impossible. Add wiki claims to `[claims]`, add wiki/manifest to D12,
  rebudget rules-reference. Also `max_check_lines = 100` is declared but enforced nowhere
  (two checks already violate it) — enforce or delete.
- **MCP surface explosion:** AC2 grows the 186-line hand-written MCP server to 60+ tools;
  needs codegen, unbudgeted.
- **"≥2 independent agent harnesses" (§10):** no workstream builds a second harness
  integration (kimi-cli is a README stub). Add one or reduce to ≥1.
- **Unowned "protocol templates":** §3 rows 12/20/31 name protocol artifacts as their
  mechanism but no workstream or deliverable produces them. Mark out-of-scope in §3 to
  match §4.7, or add an owner.
- **Row 21 Conventional Commits:** leverage named but no implementing workstream; attach
  to W5/W18 or drop.
- **Missing program meta:** no versioning/release plan (phases → v0.4-v0.8?), no
  check-rename deprecation policy (checks are user-configured by name — renames break
  configs), no rollback strategy, no staffing assumption for ~15-20 phase-weeks.

---

## 4. Leverage Verification Table (external claims, web-verified)

| SOW claim | Verdict | Evidence |
|---|---|---|
| Spec Kit constitution + `/clarify` interview | Accurate (names imprecise: `/speckit-constitution`, `/speckit.clarify`); MIT, actively maintained | [github/spec-kit](https://github.com/github/spec-kit) |
| "None of them make the spec govern the code or verify the result" | **Falsifiable as written** — OpenSpec ships `openspec validate --strict` (deterministic CLI validator); Spec Kit has `/speckit.analyze` + converge loop; BMAD v6 has a Verify phase; Kiro has Agent Hooks. The defensible claim is narrower: their verification is structural-only or LLM-mediated; none gates code/commits/CI deterministically | [OpenSpec cli docs](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) |
| "Static specs, drift managed by hand" (OpenSpec) | Wrong for OpenSpec — delta-archive automatically syncs living specs; rescope to Spec Kit | [OpenSpec](https://github.com/Fission-AI/OpenSpec) |
| OpenSpec ADDED/MODIFIED/REMOVED delta model | Accurate, precisely as described; MIT, actively maintained (Node ≥20 — its validator can't be wrapped from a Python core; emit-and-validate-in-CI or reimplement grammar with an ADR) | [OpenSpec docs](https://openspec.dev/docs/cli) |
| BMAD as SDD authoring tool | Approximately right (it is multi-agent agile orchestration); MIT, very active | [bmad-code-org](https://github.com/bmad-code-org) |
| Kiro uses EARS | Accurate; but Kiro is proprietary — artifact source only, never a leveraged dependency | [AWS Kiro](https://www.developersdigest.tech/blog/aws-kiro-developer-guide-2026) |
| Backlog.md task conventions (AC, DoD, dependencies, milestones) | Exists, MIT, active; but AC/DoD are **body sections**, not frontmatter; and its serializer **strips unknown frontmatter keys on edit** — co-editing unsafe | [MrLesk/Backlog.md](https://github.com/MrLesk/Backlog.md) |
| MADR "compatible with adr-tools/log4brains" | MADR itself: accurate (MIT/CC0, active). **adr-tools claim wrong:** Nygard-format only, GPL-3.0+, unmaintained since 2024-04 — fails the SOW's own §7 adoption criteria. log4brains: MADR-compatible but dormant since 2024-12 | [adr/madr](https://github.com/adr/madr), [npryce/adr-tools](https://github.com/npryce/adr-tools) |
| import-linter contracts | Accurate; BSD-2-Clause, Python ≥3.10; single maintainer (bus-factor note); `[boundaries]`→contracts mapping needs layers + forbidden, not "1:1" | [PyPI](https://pypi.org/project/import-linter/) |
| dependency-cruiser (JS) wrapped | Exists, MIT, very active — but **Node.js; cannot be a pip extra** | [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) |
| pip-audit | Fully accurate: Apache-2.0, ≥3.10, PyPA-maintained, pip-installable | [pypa/pip-audit](https://github.com/pypa/pip-audit) |
| OSV-scanner | Exists (Apache-2.0) but **Go binary, no PyPI package**; functionally redundant with pip-audit for Python | [google/osv-scanner](https://google.github.io/osv-scanner/) |
| Scancode | Works but heavy: 76 install dependencies, mixed license expression (bundled copyleft components) — disclose in the adoption ADR | [PyPI](https://pypi.org/project/scancode-toolkit/) |
| licensee | Redundant with Scancode (LICENSE-file detection only) and a Ruby runtime — drop | [licensee](https://github.com/licensee/licensee) |
| OpenSSF Scorecard data | Exists; API covers only repos with published results; local runs need GITHUB_TOKEN; no offline mode | [ossf/scorecard](https://github.com/ossf/scorecard) |
| in-toto/SLSA for session-log attestation | Category error — see B6. in-toto (Apache-2.0, Python) is viable as an optional parallel export, not "SLSA provenance" | [slsa.dev](https://slsa.dev) |
| aider repo map design (tree-sitter, tags cache, PageRank, binary-search budget) | Accurate against aider source; Apache-2.0. "50×" is an edge-weight multiplier, distinct from the personalization vector. Cache is `diskcache` — reimplement with stdlib sqlite3 | [aider repomap.py source](https://raw.githubusercontent.com/Aider-AI/aider/main/aider/repomap.py) |
| tree-sitter "pip-installable wheels" | Premise holds, but `tree-sitter-languages` is abandoned; use `tree-sitter-language-pack` (MIT, ≥3.10, active) | [PyPI](https://pypi.org/project/tree-sitter-language-pack/) |
| Serena MCP as reference | Valid reference, but **application is GPL-3.0-or-later** (only SolidLSP is MIT) — design reading only, no code porting | [oraios/serena LICENSE](https://github.com/oraios/serena/blob/main/LICENSE) |
| Laya model card numbers (0.362/0.461, ~800 MB, 33 ms, Apache-2.0) | Verified verbatim — but 33 ms is T4 GPU (CPU 193-464 ms), "512-token budget" misstates the head/context split, and the torch stack (~2.5+ GB) plus `noul` defect (#156) and calibration limits are omitted | [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) |
| ISO/IEC 25010 category list | **Wrong** — the SOW lists the superseded 2011 edition (8 characteristics). 25010:2023 has 9: functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility, safety. Also: "functional suitability" is not an NFR category | [ISO 25010:2023](https://www.sonarsource.com/resources/library/iso-iec-25010-explained/) |
| EARS five patterns | Accurate (Mavin et al., Rolls-Royce, IEEE RE'09 — add attribution) | [EARS](https://www.trace.space/blog/how-to-write-good-requirements-from-clarity-to-validation) |
| Gherkin → pytest-bdd / behave | Accurate: pytest-bdd 9.0.0 (MIT, ≥3.10, pytest-dev org, 2026-09 release) is the lower-risk primary; behave had a 2018→2024 release gap (record in adoption ADR) | [pytest-bdd](https://pypi.org/pypi/pytest-bdd/json) |
| ISO 29148, MoSCoW, INVEST, Conventional Commits, StrictDoc RTM | All accurate. StrictDoc: Apache-2.0, ≥3.10, active — valid as design reference | [strictdoc](https://github.com/strictdoc-project/strictdoc) |

---

## 5. Prioritized Amendment List

Ordered by "unblocks the most":

1. **Fix the check-config merge bug (B1)** — Phase 0 prerequisite, plus regression test and
   the wiki §11 starter-config correction. This is a live bug harming adopters today.
2. **Add session-log schema v2 as a Phase 1 infrastructure workstream (B4)** — task_id,
   session_id, SESSION_START/END, TEST_RESULT, HUMAN_FEEDBACK, versioned reader. Unblocks
   W6, W8, W9 detection, W17, W19, W20.
3. **Define the approval/signature trust model (B2)** — mechanism, CI story, and the
   "integrity ≠ authorship" caveat. Unblocks AC1/AC11/W0b/W1.
4. **Make AC10 measurable or demote it (B3)** — one ceiling, a measurement method, a
   recorded baseline.
5. **Resolve the W7/W10 sequencing (B5)** — W7a degraded form in Phase 2 or move to Phase 3.
6. **Rescope the three overpromising checks (B7, B8)** — `decision_drift` to declarative
   policy; `requirement_conflict` to `requirement_duplicate`.
7. **Rewrite the positioning sentence and W14 attestation (B6, §4 table row 2)** — the
   narrower true claim is just as strong; attestation becomes an optional parallel export.
8. **Split W13/W14 by distribution reality** — pip extras vs external binaries; drop
   licensee and OSV-scanner (Python path); add network-degradation outcomes to AC6.
9. **Restate W5 as a conductor migration** with hybrid design, migrator deliverable,
   one-way Backlog.md import (or body-section governance), and status/ID mapping spec.
10. **Fix W20's data story and primitives (B9)** — choice-not-noul, calibration step,
    minimum-data gate, real footprint.
11. **Re-estimate with prerequisites** — Phase 1 split (W2 alone is 3-4 weeks); Phase 2 to
    4-5 weeks (or move log v2 out); Phase 4 split; budget conductor/parser hardening and
    the forced `cli.py` split (601 lines vs `max_lines = 610`) explicitly.
12. **Housekeeping** — ISO 25010:2023 list; drop adr-tools claim; name
    tree-sitter-language-pack; Serena GPL flag; Spec Kit command names; EARS attribution;
    add wiki.md to `[claims]` and D12; rebudget rules-reference.md; enforce or delete
    `max_check_lines`; add versioning/rename/rollback policy; add §9 rows for the merge
    bug, inert severity overrides, self-hosting toil, dogfooding tax, bus factor, and
    MCP-surface explosion.

---

## 6. Notes on the SOW Document Itself

- **No frontmatter** — `drifter validate` errors on it (every markdown file under the
  docs directory requires a
  `type:`). It is declared in `drifter-manifest.toml` as of this critique (tree_integrity
  housekeeping), but the frontmatter gap remains; either add frontmatter or place it under
  a doc-type exemption. A governance program's SOW failing that program's validator is
  worth fixing before the document is circulated.
- **Future-dated:** header says 2026-10-07; repo state and this review are 2026-10-06.
- **"35 sections" vs 36 matrix rows** (rows 0-35): note that row 0 is additive.
- **§3 row 34 "Model independence: Covered"** overstates — `fastmcp` is declared nowhere in
  `pyproject.toml`; current state is Partial (AC2 itself treats the fix as a prerequisite).
- **§4.0 "core remains stdlib-only"** is literally false on Python 3.10 (`tomli` is a
  conditional runtime dep); align with AC8's "no **new** core runtime dependencies."
- **W15 state-name typo:** "IN DEVELOPMENT" contains a space while all other states are
  single tokens — a machine-enforced state machine should ship consistent tokens.

---

## 7. Bottom Line

Adopt the strategy; amend the spec. The leverage-first repositioning is coherent, the
niche (enforcement beneath spec-authoring tools) survives scrutiny once the positioning
sentence is narrowed, and the leverage matrix is 90% accurate — rare for a document this
ambitious. But three things must happen before Phase 0 starts: fix the config-merge bug
(B1), add session-log v2 to Phase 1 (B4), and define the approval/signature trust model
(B2). Without those, the program's own acceptance criteria cannot be met by its own rules.
