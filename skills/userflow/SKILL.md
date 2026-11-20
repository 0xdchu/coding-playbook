---
name: userflow
description: Design or review a software user flow to a defensible standard — one primary actor and goal, entry and exit, happy path, decision and error branches with recovery, a flow-spec table, accessibility notes and measurable success criteria; grounded in ISO 9241-210/11/110, ISO/IEC 25010 and WCAG 2.2. Use when saying "design a user flow", "review this user flow", "make a flow spec", "chuẩn hóa user flow", "vẽ luồng người dùng theo chuẩn", or when a flow has no error branches, actors or success criteria. Not for sequence diagrams or code-traced request flows (use graph, which can also render the checked flow), clickable screens (use mockup), or architecture/C4 diagrams (use archify).
---

# /userflow

Turn a vague journey into a flow a team can build, test and review. The deliverable is a **flow spec** plus a diagram brief; the diagram is a view of the spec, not the spec itself.

## When to use

- A product flow is being designed, critiqued or handed to engineering.
- A diagram has boxes but no actors, entry/exit, failure paths or success criteria.
- Someone says "user flow", "flow spec", "luồng người dùng", "chuẩn hóa flow", "review flow".

## Don't use

- Sequence diagrams or code-traced request flows: use `graph`. To render the checked flow as an offline HTML diagram, use `graph` workflow or sequence; this skill owns the spec and review.
- Clickable screens or prototypes: use `mockup`.
- Architecture, C4 or service maps: use `archify` or Structurizr.

## Standards that apply

There is no ISO/IEC standard for the drawing itself. Apply the layers around it:

| Layer | Standard | What it gives the flow |
|---|---|---|
| Process | ISO 9241-210:2019 | Context, user requirements, design solution, evaluation; the flow is evaluated, not just drawn. |
| Usability | ISO 9241-11:2018 | Exit criteria: effectiveness, efficiency, satisfaction in a stated context. |
| Interaction | ISO 9241-110:2020 | Seven principles per step: task fit, self-descriptive, expectations, learnable, controllable, error-robust, engaging. |
| Quality | ISO/IEC 25010:2023 | Interaction capability as a product-quality requirement. |
| Accessibility | WCAG 2.2 / ISO/IEC 40500:2025 | Keyboard, focus, labels, error identification, contrast, target size. |
| Notation | BPMN 2.0.2 / UML 2.5.1 | Use only when a formal cross-role or software model is required; never mix notations. |

Open [reference.md](reference.md) for the full checklist, table template and review rubric.

## Steps

**Stop rule.** If actors, permissions, recovery behaviour or metric baselines are missing from the prompt or code, stop and ask. In a one-shot run, mark the gap `[?]` and the step `unmeasured`; never invent it.

1. **Fix scope.** Name one primary actor, one goal, one entry point and one exit. If two actors each make decisions, write one flow per actor and show the other as a handoff. If there are two goals, write two flows.
2. **List actors and handoffs.** Human roles, the product, external services. Mark who decides and who only receives.
3. **Write the happy path first.** Number every step. Keep the shortest path that achieves the goal.
4. **Add branches.** Decision, validation error, external failure, timeout, cancel, permission denied. Every failure branch names a recovery and where it returns; a dead end is a defect.
5. **Add preconditions and results.** State what must be true before the step and what is true after it. Include data created or changed.
6. **Annotate accessibility.** Keyboard path, focus order, label, error text, contrast, target size, no colour-only signal.
7. **Define measurement.** Completion per step, time, error rate, retry rate, drop-off. Do not invent targets before a baseline.
8. **Choose notation and write the diagram brief.** A simple flowchart for one actor is enough. Use BPMN for pools/lanes and gateways across roles; use UML activity for software logic. The brief carries actors, boundary, entry/exit, failure group, legend and source (reference §6).
9. **Draw or update the diagram, then check parity.** Every row in the spec appears in the diagram and every branch in the diagram appears in the spec. Give the brief to `graph` if an offline HTML diagram is wanted.
10. **Review against the gate.** Use the Blocker / Should fix / Nit rubric in reference §4 and fix every blocker before handoff.

## Review mode

When reviewing an existing flow, do not redraw it first. Output findings under **Blocker / Should fix / Nit** from reference §4, each with the step or file and a concrete fix. A review is done when every blocker has a disposition and the spec/diagram parity check has run.

## Flow spec (required)

| # | Step | Actor | Precondition | Result | Failure / recovery |
|---|---|---|---|---|---|
| 1 | Entry | actor | how they arrive | what opens | broken link, no access |
| 2 | Action | actor | required data | system response | validation, retry, cancel |
| … | … | … | … | … | … |
| n | Exit | actor | success state | confirmation | support path |

Add a measurement column when the flow has a metric owner. Keep one row per user-visible step; backend-only steps belong in a separate technical flow.

## Review gate

- One primary actor, one goal, one entry, one exit; every node reachable.
- Happy path and at least one failure/recovery path are shown.
- Every decision has labelled exits; no unlabelled arrow.
- Actors and handoffs are explicit; permissions are not implied.
- Preconditions, results and data changes are stated.
- Accessibility notes exist for every input and error.
- Each step has a measurable success signal or is marked unmeasured.
- Notation is consistent and named; no mixing flowchart, BPMN and UML shapes.
- Checked with a real user, or a documented inspection that walks every step against ISO 9241-110 and the WCAG checklist in reference §3, with the result recorded.

## Done when

- The flow spec table is complete and stored next to the diagram.
- The diagram matches the table; every branch in one appears in the other.
- A reviewer can trace entry → exit and every failure → recovery without asking a question.

## Don't

- Don't draw a "user flow" that is only screens in a line.
- Don't invent metrics, actors, permissions or error behaviour.
- Don't publish internal mechanisms or secrets in a public flow.
- Don't use BPMN/UML decoration without the semantics.

## Eval

| Metric | How to measure | Target |
|---|---|---|
| Flow completeness | Review gate items passed on a real flow | no blocker findings (reference §4) |
| Branch coverage | Failure/recovery paths present vs identified risks | every high-risk path has one |
| Spec/diagram parity | Steps and branches in table vs diagram | 100% match |
| Review usefulness | Reviewer questions that the spec could not answer | 0 |

## Feedback log

| Date | What happened | What changed |
|---|---|---|
| 2026-11-20 | First version, built from an ISO/WCAG review of a public product flow | Added flow spec, failure band, accessibility and measurement sections |
| 2026-11-20 | Fresh-agent trial on an invite/accept case: it split into two actor flows, marked metrics unmeasured, and asked whether two deciding actors need one flow or two | Step 1 now says one flow per deciding actor; added the stop rule for missing actors, permissions and baselines |
