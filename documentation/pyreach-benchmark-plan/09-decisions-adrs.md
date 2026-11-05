# 09 — Architecture decision records (draft and required new entries)

## ADR workflow
For every high-impact decision create a separate `docs/adr/adr-NNN-slug.md` with **Status (Proposed/Accepted/Superseded), Context, Options, Decision, Consequences, Evidence, Owner, Date**. Status `Accepted` requires owner approval where contract/infrastructure behavior changes. No retroactive false approvals.

### ADR-001 (PROPOSED): exposing call graph for benchmarks
**Context:** the documented PyReach CLI outputs SARIF, not a graph serialization. **Options:** existing read-only function API, benchmark-only bridge, internal opt-in nonpublic export, unsupported. **Provisional decision:** audit existing code first, use minimal read-only bridge only if safe; otherwise mark unsupported. **Consequences:** partial score possible; avoid inflating accuracy. **Blocking task:** S0-T1, followed by S1-T2.

### ADR-002 (PROPOSED): dataset eligibility and source hashing
**Context:** heterogeneous call-graph formats and dataset rights. **Options:** aggregate everything vs pinned eligibility ledger. **Provisional decision:** pinned SHA+licensed corpus, eligible/unsupported/blocked accounting and deduplication. **Consequences:** results may have smaller denominator but remain auditable. **Blocking task:** S0-T4.

### ADR-003 (PROPOSED): treatment of unknown reachability
**Context:** static dynamic dispatch and missing advisory symbols. **Options:** force binary classification vs ternary labels. **Decision proposal:** `reachable/unreachable/unknown` ground truth with separate coverage/abstention reporting. **Consequences:** no fabricated exploitability assurance. **Blocking task:** S2-T4.

### ADR-004 (PROPOSED): scope of Vul4Py
**Context:** vulnerability-repair oracles do not directly label dependency function reachability. **Provisional decision:** treat as auxiliary eligibility audit; only reuse verified package-symbol cases. **Consequences:** avoid unsupported head-to-head comparisons. **Blocking task:** S2-T5.

### ADR-005 (PROPOSED): offline proof
**Context:** uv offline flag alone is insufficient to prove process-wide network absence. **Provisional decision:** frozen offline execution in denied-network sandbox, record enforcement. **Consequences:** WSL2 environment may need different isolation mechanism. **Blocking tasks:** S0-T3, S4-T1.

## Required gate
Change any `PROPOSED` to `Accepted` only after recording actual source audit/evidence and an owner decision in `tracking/approval-gates.md`.
