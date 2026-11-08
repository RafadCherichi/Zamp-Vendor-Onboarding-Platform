# Zamp PS-2 prototype grading rubric

**Proposed for approval • Version 1.0 • 8 November 2026 • Current prototype ungraded**

## The decision this score supports

Would a procurement lead trust this candidate to turn a messy vendor submission into a working, understandable decision process? Grade one week of prototype work against the candidate guide. A realistic synthetic submission is a valid input. A simulated registry is acceptable when its contribution is labelled accurately. The project specification gives us the intended buyer, roles and policies. The candidate guide determines the assignment.

The proposed 100 points allocate 38 to execution and decision behaviour, 32 to the information and interface people use, 22 to PM and consulting judgment, and 8 to communicating a live result. These weights express our priorities for this case. Zamp has not published them. The external sources below inform the checks. They do not establish the weights or predict a hiring decision.

## Scorecard

Each dimension has four equally weighted checks. Record **1** for demonstrated, **½** for partly demonstrated, **0** for an observed failure or confirmed absence, and **U** for unexamined evidence. Full credit requires every material part of a check in the applicable scenarios. Give half credit when the core behaviour works but a specified part is missing, breaks in one applicable scenario, or requires moderator help. State exactly which part. An appearance of functionality in a screenshot cannot establish that an action works.

| Dimension | Weight | Four checks, scored separately |
|---|---:|---|
| A. Live execution and workflow visibility | 20 | **A1** Start with a fresh realistic form and document through the ordinary vendor interface. **A2** Change one material input and observe the corresponding extracted value or check change. **A3** While work runs, the user sees truthful feedback about what is happening, followed by the result. Instant operations can show immediate confirmation. **A4** The resulting case, status and reference survive refresh and appear consistently in the vendor view and staff queue. |
| B. Decision correctness and exception recovery | 18 | **B1** A complete, consistent case reaches the expected human approval decision. **B2** A material conflict triggers the agreed block and the right owner can resolve it. **B3** A provider outage or ambiguous identity stays uncertain and reaches the appropriate reviewer or retry path. **B4** After a correction, the system checks the affected evidence again, preserves history and enforces the resulting decision, including when the correction is still wrong. |
| C. Content richness and evidence | 12 | **C1** The vendor sees which evidence applies to this business and why. **C2** For a disputed field, the reviewer can compare the submitted value with the value on the relevant document version. **C3** The reviewer can tell which claims come from the vendor, extraction, a rule, a simulation or a person. **C4** The queue and history together answer who owns the case, what changed, what remains open and why the latest decision was made. |
| D. PM judgment and outcome measurement | 12 | **D1** Identify the target user, the task that repeatedly causes friction and a concrete consequence. **D2** Show a choice made within one week, the alternative deferred and the user or business reason. **D3** Define a primary outcome with a unit, population and collection method, plus a risk measure and baseline or baseline plan. **D4** Trace one observed problem through a product change and a follow-up check that shows what improved or still needs investigation. |
| E. Consulting reasoning and buyer value | 10 | **E1** Describe the manual process and identify a specific failure at a handoff. Mark assumptions about a buyer separately from observed facts. **E2** Distinguish causes that require different responses, such as an entry error, uncertain document reading and an unavailable registry. **E3** Explain the recommended action, its owner, and the cost of acting or waiting. **E4** Estimate value with visible assumptions and units, identify a driver that could change the conclusion, and say what a pilot would measure. |
| F. Human language and comprehension | 10 | **F1** A first-time vendor can paraphrase the submission status correctly. **F2** On a correction request they can identify the discrepancy, the specific action and where to take it. **F3** On an outage they can tell whether they need to act and who acts next. **F4** They can explain any term needed for the task using the available labels, example or help. Tone stays respectful and avoids blaming the vendor for service failures. |
| G. Visual presentation and accessibility | 10 | **G1** On first viewing, a user can locate the current status and primary action without a hint. **G2** At normal screen-sharing size, related evidence reads together, headings and controls are consistent, and important content is legible without zooming the recording. **G3** The vendor can complete the correction on a phone and staff can review evidence on a laptop without losing a critical field or action. **G4** On the sampled path, keyboard operation, visible focus, text labels for status, and contrast support use. For ordinary text use WCAG's 4.5:1 AA criterion where applicable. |
| H. Five-minute live demonstration | 8 | **H1** An evaluator can open the runnable process and follow the prepared happy path. **H2** One recording or timed rehearsal within five minutes shows a happy path and at least one edge case executing. **H3** A nontechnical viewer can recount the input, decision and buyer consequence after watching. **H4** The presenter can show what ran, identify what was simulated and explain one design trade-off during follow-up. |

**Calculation.** Dimension points = weight × sum of the four check values ÷ 4. Add dimension points and round only the final total to one decimal. Example only: scores of 1, 1, ½ and 0 on C earn 12 × 2.5 ÷ 4 = **7.5/12**. Every check has its own evidence line. The same event can supply evidence for different questions. A bank mismatch can earn B2 for blocking approval even when poor wording earns no F2 credit.

**Missing evidence.** Keep U visible. Until all checks are assessed, report a range. The lower bound treats U as zero and the upper bound gives each U full credit. Report assessed weight alongside it. This allows a product review to proceed before the recording or first-time-user session. A rehearsal can demonstrate the quality of the five-minute story. Track the actual deliverables separately as two yes/no items: accessible runnable link and accessible recording of five minutes or less.

**Readiness condition.** Show the numeric score alongside a separate result for core PS-2 behaviour. To mark that behaviour demonstrated, require a fresh submission to reach a reasoned status, two meaningfully different prepared edge cases to behave as specified, and a pending or rejected vendor to receive the reason and applicable next step. If the case policy blocks approval for conflicting bank evidence, a successful approval with the conflict unresolved fails this condition. An unrun scenario stays unverified. Keep the score for diagnosis even when the condition fails. The guide allows two to four designed edge cases and asks for at least one in the video.

## How to collect comparable evidence

Use a disposable demo database and upload directory. Write expected decisions before running cases. Record build, fixture, role, device, expected and observed result, and screenshot or timestamp. Where a decision permits more than one human outcome, agree on the allowed states and required justification in advance.

| Test | Input and expected behaviour | What it reveals |
|---|---|---|
| Fresh happy path | Submit a complete synthetic business and readable proofs. Consistent evidence should lead to eligibility, followed by a recorded reviewer decision and vendor-visible outcome. | Whether an evaluator can watch new input become an output through the normal interface. |
| Material bank mismatch | Change only the last digits in the form while keeping the cheque fixed. Try approval while blocked. Submit a still-wrong correction, then a matching correction. | Whether the rule follows evidence, protects the decision and lets the vendor recover. |
| Registry unavailable | Keep business data consistent and simulate one external timeout. Inspect what the vendor, reviewer and queue each say. | Whether the system distinguishes an unknown result from adverse evidence and assigns the next action correctly. |
| Optional precision probe | Use an unreadable required document, or a plausible name abbreviation with otherwise consistent identifiers. Write the expected treatment first. | Whether the process requests better evidence or human review when the facts are ambiguous. No bonus for adding cases. |

For F and G, give a first-time participant a goal such as “Help this vendor get their application moving again.” Let them use the product before explaining the screen. Record their first answer, action, help needed and outcome. A colleague can act as a proxy if identified as such. One session gives qualitative evidence about that participant. Record broader usability as untested. For H3 ask the viewer what happened and why, after the rehearsal. An evaluator can gather most other evidence from the live product and a short decision note or interview.

Two graders can independently record each check, compare evidence and resolve disagreements against the written criterion. For a close call, retain the original observation and record the reason for the final mark. Report the eight subscores so a total cannot conceal a weak area. Priority for any later fixes follows buyer impact and failed core behaviour.

## What the judgment checks mean in this case

**A suitable primary product KPI** is median elapsed time from first submission to recorded approval or rejection for decided applications in a defined cohort. Compare the same types of vendors and separately report open-case count and age, since the median excludes unresolved cases. An alternative focused on the product's differentiator is median time from a correction request to a valid resubmission. Pair speed with the proportion of known blocking cases incorrectly approved in a labelled evaluation set. Cite numerator, denominator and sample size. A pilot baseline plan earns credit under D3. Synthetic trials establish behaviour on the fixtures.

**A consulting example** is an estimate of reviewer capacity released. If a buyer processes an assumed 80 applications per month, 25% require correction, and targeted correction saves an assumed 12 minutes of staff time per affected case, the estimate is 4 staff-hours per month. At 6 minutes saved it falls to 2 hours. A pilot could time active reviewer effort for comparable cases. The numbers are illustrative. Elapsed days waiting for a vendor and active staff minutes measure different costs.

**A language example** for the mismatch is “The account number you entered ends in 4821. Your cheque shows 4281. Check which account you want us to use, then update the number or upload the matching proof.” For an outage, if staff own the follow-up, appropriate copy is “We couldn’t reach the registry. Your application is with our review team. You don’t need to upload the certificate again.” Score whether the product offers the action promised in the message.

## Research behind the criteria

| Source | Application to the rubric |
|---|---|
| [Zamp candidate guide](./ASA%20Case%20Study%20%E2%80%94%20Candidate%20Guide.pdf), pages 1–2, 4, 6–7 | Sets the expected inputs, reasoned outcomes, case count, runnable process, demonstration and audience. |
| [GOV.UK Service Standard](https://www.gov.uk/service-manual/service-standard) | Assess the complete journey across vendor and procurement roles, including the result of the handoff. |
| [Nielsen Norman Group, visibility of system status](https://www.nngroup.com/articles/visibility-system-status/) | Inspect feedback during execution as well as the saved result. |
| [Microsoft Research, human-AI interaction guidelines](https://www.microsoft.com/en-us/research/uploads/prod/2019/03/AI_Guidelines_Poster_PrintQuality.pdf) and [NIST, Four Principles of Explainable AI](https://nvlpubs.nist.gov/nistpubs/ir/2021/NIST.IR.8312.pdf) | Test recovery from incorrect extraction, whether an explanation reflects the actual reason, whether the audience understands it, and how uncertainty affects action. |
| [India Income Tax Department, Verify Your PAN](https://www.incometax.gov.in/iec/foportal/help/how-to-verify-pan) | Official PAN status verification has its own process. Grade the precision of labels for format checks, extracted text and simulated or authoritative results. |
| [UK Digital and Data Profession Capability Framework](https://understand-digital-data-roles-skills.service.gov.uk/skills/) and [Google Research, HEART](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/) | Ask for an observable outcome, a defensible metric and a decision informed by evidence. |
| [McKinsey, seven-step problem solving](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/how-to-master-the-seven-step-problem-solving-process) | Observe problem definition, decomposition, prioritisation and synthesis through a specific buyer recommendation. |
| [GOV.UK Design System, error messages](https://design-system.service.gov.uk/components/error-message/) and [check answers](https://design-system.service.gov.uk/patterns/check-answers/) | Inspect the precise correction requested, its placement, and whether users can review an answer before committing it. |
| [Nielsen Norman Group, visual design principles](https://media.nngroup.com/media/articles/attachments/Principles_Visual_Design-A4.pdf) and [W3C, WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Assess hierarchy, grouping, contrast, focus, keyboard use and colour-independent status on named tasks. This sample supports a scoped accessibility finding. |
| [GOV.UK, moderated usability testing](https://www.gov.uk/service-manual/user-research/using-moderated-usability-testing) | Give the participant a realistic task and observe independent behaviour before coaching. |

## Grading record

For each of A1–H4 record: **check ID | mark (1, ½, 0, U) | expected | observed | evidence reference | grader**.

Final review: **points or range / 100 | assessed weight | eight subscores | core behaviour demonstrated, failed or unverified | runnable link | recording | material evidence limitations**.
