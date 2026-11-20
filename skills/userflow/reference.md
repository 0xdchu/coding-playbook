# User flow reference

## 1. Standards in detail

| Standard | Use | Link |
|---|---|---|
| ISO 9241-210:2019 | Human-centred design process: understand context, specify requirements, produce design solutions, evaluate. The flow is a design artifact and must be evaluated. | https://www.iso.org/standard/77520.html |
| ISO 9241-11:2018 | Usability: effectiveness, efficiency, satisfaction in a specified context of use. Use these as exit criteria. | https://www.iso.org/standard/63500.html |
| ISO 9241-110:2020 | Seven interaction principles: suitability for the user's tasks, self-descriptiveness, conformity with user expectations, learnability, controllability, use error robustness, user engagement. | https://www.iso.org/standard/75258.html |
| ISO/IEC 25010:2023 | Product quality model; interaction capability. Use for quality requirements and acceptance criteria. | https://www.iso.org/standard/78176.html |
| WCAG 2.2 / ISO/IEC 40500:2025 | Web accessibility. Use for keyboard, focus, labels, errors, contrast, target size, reflow. | https://www.w3.org/TR/WCAG22/ · https://www.iso.org/standard/91029.html |
| BPMN 2.0.2 | Formal business-process notation: pools, lanes, events, gateways. Use when roles/systems cross boundaries. | https://www.omg.org/spec/BPMN |
| UML 2.5.1 | Formal software notation: activity diagrams for logic, sequence diagrams for interactions. | https://www.omg.org/spec/UML/2.5.1 |

There is no ISO/IEC standard for the shape of a user-flow diagram. The standards constrain the process, the quality of each step and the evaluation; the drawing is a communication choice.

## 2. Flow spec template

```md
# <Flow name>

- Actor:
- Goal:
- Entry:
- Exit:
- Context / constraints:
- Notation: flowchart | BPMN | UML activity

| # | Step | Actor | Precondition | Result | Failure / recovery | Measure |
|---|---|---|---|---|---|---|
| 1 | Entry | | | | | |
| 2 | | | | | | |
| n | Exit | | | | | |

## Decisions
| ID | Question | Yes | No |
|---|---|---|---|
| D1 | | | |

## Failure paths
| Risk | Detection | Recovery | Returns to |
|---|---|---|---|
| | | | |

## Accessibility
- Keyboard:
- Focus order:
- Labels / errors:
- Contrast / target size:
- Reflow / zoom:

## Metrics
| Metric | Definition | Baseline | Target |
|---|---|---|---|
| Completion | | | |
| Time | | | |
| Error rate | | | |
```

## 3. WCAG 2.2 checklist for a flow

- Every action is reachable with a keyboard; no keyboard trap.
- Focus is visible and follows reading order.
- Inputs have programmatic labels; errors identify the field and say how to fix it.
- Status messages are announced without moving focus.
- Colour is not the only signal; contrast meets AA.
- Target size is at least 24×24 CSS px, or has equivalent spacing.
- Content reflows at 320 CSS px without loss of information.
- Time limits can be extended; users can pause, stop or hide motion.
- Authentication does not rely on a cognitive test; allow paste/password managers.

## 4. Review rubric

### Blocker

- No actor, goal, entry or exit.
- A decision with an unlabelled or dead-end branch.
- A failure path with no recovery.
- The spec and diagram disagree on steps or branches.
- A claim about users, metrics or permissions with no source.

### Should fix

- Preconditions/results missing.
- Accessibility notes missing for inputs or errors.
- Metrics present but undefined.
- Notation mixed or unlabelled.
- One flow contains several goals.

### Nit

- Step wording, order of legend items, line routing.

## 5. Common mistakes

- Drawing screens instead of decisions and state changes.
- Treating the happy path as the whole flow.
- Hiding recovery in a tooltip or support article.
- Using a journey map where a task flow is needed, or the reverse.
- Adding BPMN shapes without pools, events and gateway semantics.
- Publishing backend mechanisms or secrets in a public flow.

## 6. Diagram brief

When handing the flow to a diagram tool, give it:

1. The flow spec table.
2. The actor list and the system boundary.
3. The notation and direction.
4. The entry and exit markers.
5. The failure/recovery group, drawn separately from the happy path.
6. The legend: actor, decision, external platform, failure.
7. The source and date.

The diagram is done when a reader can trace entry → exit and every failure → recovery without asking a question.
