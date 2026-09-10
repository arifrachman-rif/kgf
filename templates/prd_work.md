<!--
AUTHORING RULES. Read before writing. Delete this block in the final document.

STRUCTURE (this is what makes the Google Doc readable):
1. Spec content goes in a TABLE. Any section describing an endpoint, a state, a rule,
   a field, or a config is a table, never a run of sentences. Default shape:
   | Attribute | Detail |
2. Parallel items go in BULLETS, one item per line, each starting with "- ".
   Put a bold lead-in on its own line above the list when the list needs a label.
3. A connected argument goes in ONE PARAGRAPH of flowing prose.

NEVER write bare consecutive sentence-lines with no marker. In markdown those are not a
list, they are one paragraph, and they convert into an unreadable wall of text.
"Lists one item per line" means every BULLET gets its own line. It does not mean
every SENTENCE gets its own line.

MANDATORY BLANK LINE before every table and before every bullet list. The converter
silently breaks the block without it.

STYLE: English. Never the em-dash character. No parenthetical asides as filler.
Do not invent owners, dates, or estimates; unknowns go to Open Questions.

DIAGRAMS: write mermaid, validate it renders, then swap the fence for a [[PLACEHOLDER]]
and register it in scripts/embed_mermaid_in_gdoc.py. See .agent/skills/diagram-gen/SKILL.md.

PUBLISH: never hand-run the steps. Use scripts/publish_prd.sh, which converts, embeds
diagrams, runs the formatting pass, enforces the readability gate, and re-restricts last.
-->

# PRD: [Feature Name]

| Field | Value |
|:---|:---|
| Project | [Project Name, e.g. Seller Portal, B2C SuperApp] |
| Feature | [Feature Name] |
| Status | Draft |
| Owner | Your Name |
| Version | v0.1 |
| Date | [YYYY-MM-DD] |

---

## Executive Summary

### The Why
[Problem statement. What user or business pain does this solve? One flowing paragraph, not sentence-per-line.]

### The What
[High-level description of the solution in 2 to 3 sentences. One paragraph.]

---

## Success Metrics

| Metric | Baseline | Target | How Measured |
|:---|:---|:---|:---|
| [e.g. Conversion Rate] | [Current %] | [Goal %] | [Analytics tool / method] |
| [e.g. Task Completion Time] | [Current] | [Goal] | [How] |

---

## User Stories

| # | As a... | I want to... | So that... | Priority |
|:---|:---|:---|:---|:---|
| 1 | [User type] | [Action] | [Benefit] | P0 |
| 2 | [User type] | [Action] | [Benefit] | P1 |

---

## Feature Requirements

### Phase 1, P0 (Must Have)

| # | Requirement | Notes |
|:---|:---|:---|
| 1 | [Requirement description] | |
| 2 | [Requirement description] | |

### Phase 2, P1 (Should Have)

| # | Requirement | Notes |
|:---|:---|:---|
| 1 | [Requirement description] | |

### Out of Scope

- [Item explicitly excluded]
- [Item explicitly excluded]

### MCP Companion (mandatory for every EXTERNAL-PARTNER API or SDK product)

> Standing rule (17 Jul 2026, scope clarified by the owner 30 Jul 2026): any API or SDK product built for **external partners** **always** ships an accompanying **MCP (Model Context Protocol) server** exposing the **same capabilities** as the API or SDK surface.
>
> **Internal APIs do not need this.** The test is who consumes it, not whether an HTTP endpoint exists. Service-to-service calls between Work components, contracts between Work's backend and Work's own frontend, and endpoints used only by Work CS or admin tooling are all internal. Delete this subsection for those.
>
> External means a partner, a tenant, or a bank integrates against it. The Storefront API for Bank al-Etihad, the Seller Portal external API for partner sellers, the Work Fulfillment Service, Storefront Analytics, and any SDK a tenant embeds all require the block.
>
> **Intent counts, not just current state.** A service meant to be opened to external partners later needs this block now. Retrofitting capability parity after the API surface is fixed is a rewrite. The Fulfillment Service is the worked example: it looks internal today and correctly carries the block because it is intended to open externally.

| # | Requirement | Notes |
|:---|:---|:---|
| M1 | Every API capability or SDK method has a matching MCP tool with equivalent inputs, outputs, errors, auth, and tenant scoping | Capability parity, not a curated subset |
| M2 | The MCP server reuses the same auth and tenant-isolation model as the API (no second security surface) | |
| M3 | The MCP server is versioned and documented alongside the API, in the same release, not a later phase | First-class deliverable |
| M4 | Parity is a release gate: an API/SDK capability is not "done" until its MCP tool exists, is tested, and is documented | |

- Any capability intentionally NOT exposed via MCP is listed here with a reason: [none, or list]

---

## System Architecture

### Architecture Diagram
[[ARCH_DIAGRAM]]

### Integration Contracts

| Integration | Direction | Protocol | Payload | Error Handling |
|:---|:---|:---|:---|:---|
| [Service A to Service B] | [Outbound] | [REST/HTTPS] | [Shape] | [Behavior on failure] |

---

## Functional Specification

> One subsection per endpoint, state, or rule. Each one is a TABLE, never prose lines.

### [Endpoint or Rule Name, Phase N]

| Attribute | Detail |
|:---|:---|
| **Purpose** | [What it does, one sentence] |
| **Reused path** | [Existing mechanism it writes through, with ticket ID, or "net new"] |
| **Inputs** | [Required and optional fields] |
| **Behavior** | [What happens on success] |
| **Constraints** | [Limits, throttles, ownership scoping] |
| **Errors** | [Failure modes and what the caller sees] |

### [State Machine, if applicable]

| State | Meaning | Entered when | Terminal |
|:---|:---|:---|:---|
| [STATE_NAME] | [What it means] | [Trigger] | [Yes/No] |

---

## Acceptance Criteria

**Scenario: [Happy path name]**

```gherkin
Given [precondition]
And [precondition]
When [action]
Then [observable outcome]
And [observable outcome]
```

**Scenario: [Failure or edge case name]**

```gherkin
Given [precondition]
When [action]
Then [rejection with a specific, actionable error]
```

---

## Non-Functional Requirements

| Category | Requirement | Target |
|:---|:---|:---|
| Security | [e.g. tenant-scoped tokens] | [Measurable bar] |
| Performance | [e.g. p95 latency] | [Number] |
| Auditability | [e.g. every write logged] | [Retention] |
| Monitoring | [e.g. alert on error rate] | [Threshold] |

---

## Open Questions

| # | Question | Owner | Due |
|:---|:---|:---|:---|
| 1 | [Question to resolve] | [Name, or TBD] | [Date, or TBD] |

---

## Dependencies & Risks

| Type | Description | Mitigation |
|:---|:---|:---|
| Dependency | [e.g. Requires OMS API v2] | [Plan B] |
| Risk | [e.g. Third-party integration delay] | [Mitigation] |

---

## Revision History

| Revision | Date | Summary |
|:---|:---|:---|
| v0.1 | [YYYY-MM-DD] | Initial draft |
