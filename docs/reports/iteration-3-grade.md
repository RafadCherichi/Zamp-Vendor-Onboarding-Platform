# Zamp PS-2 prototype: iteration 3 grade

9 November 2026 · graded against the approved [100-point rubric](../product/grading-rubric.md)

**81–93/100; 88/100 points assessed.** The lower end assigns zero to unexamined checks; the upper end awards them full credit. This is an evidence-based prototype grade, not a prediction of an evaluator's hiring decision. The 14-case workbook remains synthetic and does not establish real-world accuracy.

## Scorecard

| Dimension | Check marks in rubric order | Points | Evidence and limits |
|---|---|---:|---|
| A. Live execution and workflow visibility | A1 1, A2 1, A3 1, A4 1 | **20/20** | Fresh browser entry, upload, submission, refresh and reviewer decision are captured in [the browser run](../../testdata/fresh_browser_results.json). A delayed upload showed the actual “Reading the document” stage, and backend checks observed stages persisted before OCR, classification and extraction. The same reference and decision appeared in vendor and staff views. |
| B. Decision correctness and exception recovery | B1 1, B2 1, B3 1, B4 1 | **18/18** | The [scenario results](../../testdata/scenario_results.json) cover clean approval, a bank conflict, unreadable proof, an unavailable simulated provider, a wrong-slot document and wrong then matching corrections. A current bank-conflict browser view shows the conflicting values, a disabled approval action and the source link; approval remains blocked until the correction and exception process is complete. These results apply to labelled synthetic cases. |
| C. Content richness and evidence | C1 1, C2 1, C3 1, C4 1 | **12/12** | The [bank-conflict reviewer screen](../../grade_evidence/iteration3-bank-conflict-review.png) places the vendor-entered account beside the extracted account and links to bank proof version 1; the browser opened that exact version. A focused backend check verified old and current version bytes and rejected an unrelated version. The validation view labels vendor-entered, document-read and simulated registry evidence. The queue now shows issue count, next owner, update date and decision maker; the decision view and activity trail retain actor, time and notes. |
| D. PM judgment and outcome measurement | D1 1, D2 1, D3 1, D4 1 | **12/12** | The decision note names the buyer/vendor handoff, a one-week priority, alternatives, a primary turnaround measure, a safety guardrail and the bank-field change traced from discovery to follow-up. The evidence remains synthetic, so the pilot figures are plans rather than measured user outcomes. |
| E. Consulting reasoning and buyer value | E1 1, E2 1, E3 1, E4 1 | **10/10** | The [decision note](../case-study/decision-note.md) distinguishes facts from assumptions, separates entry error from uncertain reading and registry outage, assigns owners, and adds low/base/high estimates. It compares a one-month cost of waiting with an assumed four-hour measurement pilot and gives explicit conditions that would change the recommendation. A buyer has not validated the assumptions. |
| F. Human language and comprehension | F1 U, F2 U, F3 ½, F4 U | **1.25–8.75/10** | The wording distinguishes vendor corrections from staff-owned verification issues, but no first-time vendor has yet interpreted the status, completed the correction, explained an outage or paraphrased the terms without coaching. |
| G. Visual presentation and accessibility | G1 U, G2 ½, G3 ½, G4 ½ | **3.75–6.25/10** | The fresh reviewer queue and final-decision screens were inspected at 1440×900; the vendor form and document progress were inspected at desktop size, and earlier evidence covers 390px mobile width. The bank comparison remains a long, dense validation list at screen-share scale. First-glance tasks, a complete phone correction, keyboard travel, measured contrast and a scoped accessibility audit remain outstanding. |
| H. Five-minute live demonstration | H1 ½, H2 1, H3 U, H4 ½ | **4–6/8** | A local runnable build and short silent rehearsal show a decision and correction action. There is no evaluator-accessible public URL, no independent audience recall and no observed follow-up explanation. |

The rubric has 12 unexamined points. The exact total is **81–93/100**; points for each unknown check remain visible in the ranges above.

## New iteration evidence

- **A3:** OCR/classification/extraction stages are persisted by actual work. A deliberately delayed browser upload showed “Reading the document” before its result. The vendor can refresh without losing the application outcome.
- **C2–C4:** Reviewers can compare a disputed bank value with the proof, open the exact version, distinguish evidence sources, and see the next owner and final decision maker. The decision screen no longer reports “pending requirements” after a final decision.
- **Decision safety:** An unresolved blocker disables the approval button, rather than merely styling it to look unavailable. A browser assertion verifies the control is disabled on the seeded mismatch.
- **Vendor form reliability:** Browser evidence found a background refresh could clear the first field typed on a new step. The wizard now keeps unsaved local edits when refreshed case data arrives; the seven-step fresh browser flow passed afterward.
- **E3:** The buyer-value note now prices only active reviewer follow-up effort with explicit units. It treats vendor waiting and buyer operating loss separately because this prototype has no evidence to convert either into money.

## Verification record

- Backend regression: **109 passed, 1 warning** using the isolated regression runner and disposable SQLite database.
- Focused queue/reviewer tests: **7 passed, 1 warning**.
- Frontend TypeScript production build: passed. Frontend lint: passed with existing warnings in other shared components.
- Fresh browser flow: passed with `browser_submitted`, `refresh_preserved_status`, `vendor_approved_visible`, `staff_queue_consistent`, `live_reading_seen`, `reviewer_source_comparison_visible`, and `bank_conflict_and_source_visible` all true.
- The browser check also asserts the final decision has no pending-requirement label, the bank proof opens as version 1, and approval is disabled while blockers remain.
- Docker is unavailable in this workspace, so the container image and hosted persistence have not yet been exercised.

## Readiness and remaining work

**Synthetic core behaviour:** demonstrated for the prepared cases and the fresh browser happy path. This is not evidence of a real-world false-approval rate or first-time-user comprehension.

**Submission gate:** the GitHub repository is public and empty; the current source has not yet been pushed. The application is prepared for one-origin hosting, but no evaluator URL exists yet. A final narrated recording and first-time-user sessions are also outstanding.

The highest-value remaining evidence is a first-time vendor correction/outage session, phone completion and keyboard/contrast audit. Then push this reviewed state to the provided GitHub repository, publish the FastAPI-backed one-link app, and record a paced demo under five minutes.
