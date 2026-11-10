# Zamp PS-2 product scorecard

**Version 2.0 · 9 November 2026 · Diagnostic rubric, not an official Zamp marking scheme**

## What this score measures

The candidate guide is the authority for the assignment. PS-2 asks for a working process that accepts vendor information, reaches an explained approved, pending or rejected result, shows what needs to happen when the result is not approval, exposes the process stages while they run, and gives staff a dashboard with run history, status and outputs. The submission should deliberately handle two to four realistic edge cases and demonstrate a happy path and at least one edge within five minutes.

This score therefore gives 93 points to the product experience and its observable behavior, 4 to product/consulting judgment, and 3 to the constrained demo. The dimensions are not interchangeable: a beautiful dashboard cannot compensate for unsafe decisions, and a high score cannot waive the case-study requirements. It is an internal diagnostic, not an estimate of an evaluator's mark.

## Weighted dimensions

Score each of the four checks in a row as **1** (demonstrated), **0.5** (partly demonstrated), **0** (observed failure or confirmed absence), or **U** (not examined). Dimension points equal its weight multiplied by the average check mark. Keep U as a range; do not treat missing evidence as success.

| Dimension | Weight | Observable checks |
|---|---:|---|
| A. End-to-end working process | 24 | **A1** A new realistic vendor can enter and submit a case through the normal product. **A2** Submitted forms and documents cause the actual process to run. **A3** The resulting state, reason and case reference persist through refresh. **A4** Vendor and staff views agree about the same case and its current owner/action. |
| B. Decision quality and safety | 20 | **B1** A clean case reaches human approval with its evidence visible. **B2** A known material conflict blocks approval. **B3** Pending, rejected, unreadable and unavailable/unknown are not conflated with approval or with one another. **B4** A correction is rechecked; a still-wrong answer remains blocked and a correct answer can proceed only after required review/resolution. |
| C. Edge-case coverage | 16 | **C1** Conflicting bank details have a distinct, useful outcome. **C2** Unreadable or wrong-slot evidence has a distinct, useful outcome. **C3** An unavailable external check remains unknown and has the right next owner. **C4** Constitution-dependent evidence requirements differ correctly for the vendor type. |
| D. Live process visibility | 15 | **D1** Actual stages are shown while processing, not invented after completion. **D2** Stage names tell a non-technical user what is happening. **D3** Completion, failure or uncertainty is visible with the output. **D4** The user can follow the saved findings and resulting status back to the relevant run. |
| E. Run dashboard and inspection | 10 | **E1** Staff can find recent runs and their status. **E2** A selected run exposes its own findings and output. **E3** The decision reason, next action and current case status are clear. **E4** Simulations and source types are labelled honestly; a run links to its current case. |
| F. UI, language and presentability | 8 | **F1** Primary action and current state are easy to locate; controls align and remain consistent. **F2** Content is grouped with enough hierarchy and craft to feel like an intentional operational product. **F3** Vendor and reviewer tasks work at phone and desktop sizes without losing critical actions. **F4** Instructions are human, specific and respectful; keyboard/focus/contrast and first-time comprehension are examined. |
| G. Product and consulting judgment | 4 | **G1** Target user, painful handoff and consequence are explicit. **G2** Scope choice and deferred alternative are reasoned from that user need. **G3** A measurable outcome has a unit, cohort, time window and collection plan. **G4** A safety and counter-metric, assumptions, value model and limitations are stated without presenting hypotheses as results. |
| H. Five-minute demonstration | 3 | **H1** Runnable setup is ready for the evaluator. **H2** A timed narrated demo of five minutes or less shows the happy path and an edge executing. **H3** A viewer can explain the input, outcome and buyer consequence. **H4** The presenter accurately distinguishes implemented, simulated and unverified behavior. |
| **Total** | **100** | |

The score rounds only the final total to one decimal. For example, four check marks of 1, 1, 0.5 and U on a 12-point dimension give an assessed result of 7.5–10.5/12: U contributes zero to the lower bound and one to the upper. Report the range and assessed weight together.

## Readiness gates

Report these separately from the numeric grade:

1. A fresh, ordinary UI submission reaches a saved, reasoned result.
2. At least two different prepared edge cases behave as specified, with no known blocker incorrectly approved.
3. Non-approved cases tell the vendor the reason and the action or next owner.
4. An evaluator can access the runnable product, and the narrated demo is five minutes or less with a happy path and one edge.

An unverified gate is **not demonstrated**. Keep the score for diagnosis; never use a high percentage to imply that a failed gate passed.

## Evidence protocol

Before each run, record scenario ID, expected result, vendor type, role, browser/device, build and data reset. Capture observed status, reason, owner/action, approval attempt, refresh result and evidence file. Keep expected decisions written before running the case. For a human decision, state allowed outcomes and required justification in advance. Count scenario assertions separately from production accuracy: synthetic fixtures show that the product responds to those fixtures, not that real-world error rates are low.

For usability checks, give a first-time participant a task without a screen tour, observe their first action and words, and record help needed. Label a colleague as a proxy. Automated browser checks establish layout and behavior, not independent comprehension. Inspect keyboard focus and contrast on the same path. WCAG 2.2 AA text contrast is 4.5:1 for ordinary text where applicable.

## Why these dimensions and weights

The order follows the case: the real process and safe outcomes carry 44 points because the product must work on input, not only describe itself. Edge-case handling is 16 because the guide explicitly requires deliberate non-happy paths. Stage visibility and run inspection together carry 25 because live process visibility and history/status/output are explicit deliverables. UI and understandable language carry 8: they help vendors and reviewers complete the work, but cannot outweigh process correctness. Judgment and the five-minute story carry 7 because the case needs a credible recommendation and a compact demonstration.

The weights are our prioritization judgment. Research guides *what to inspect*, not the numerical weights: [GOV.UK Service Standard](https://www.gov.uk/service-manual/service-standard) supports judging the whole service and handoffs; [Nielsen Norman Group on system status](https://www.nngroup.com/articles/visibility-system-status/) supports truthful progress feedback; [Microsoft's human-AI guidelines](https://www.microsoft.com/en-us/research/uploads/prod/2019/03/AI_Guidelines_Poster_PrintQuality.pdf) and [NIST explainable-AI principles](https://nvlpubs.nist.gov/nistpubs/ir/2021/NIST.IR.8312.pdf) inform correction, uncertainty and explanation checks; [GOV.UK error-message guidance](https://design-system.service.gov.uk/components/error-message/) informs actionable copy; [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) informs accessibility; [Google HEART](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/) informs measurable user outcomes. The assignment guide remains primary when advice differs.

## Product measures to carry beyond the prototype

- **Primary outcome:** median elapsed hours from first submission to recorded reviewer decision for a defined four-week cohort. Always report cohort size, decided-case count, constitution segments, and the count and age of still-open cases beside it.
- **Safety guardrail:** known blocking cases incorrectly approved divided by all labelled blocking cases evaluated. Target zero on the test set; audit a sample of real pilot decisions before making a production claim.
- **Counter-metric:** correct cases incorrectly blocked. A safer workflow that holds too many valid vendors is not successful.
- **Secondary diagnostic:** median time from correction request to valid response, reported separately from active reviewer minutes and vendor waiting time.
- **Value hypothesis:** estimate reviewer capacity from observed correction share and active minutes avoided; show assumptions and sensitivity. Never count calendar waiting days as labor saved.

## Grading record

Record every check as `ID | mark | expected | observed | evidence | grader`. Final report: `score/range out of 100 | assessed weight | eight dimension scores | readiness gates | runnable URL | recording | material unknowns`.
