# PS-2 Live Process and Presentation Plan

> **For agentic workers:** This is the approved execution plan. Follow tasks in order, verify each deliverable, and record results in `progress.md` beside this plan.

**Goal:** Make the vendor-onboarding process an unmistakable, runnable PS-2 submission: accept a realistic vendor input, execute checks live, return an explained approved/pending/rejected result, show each actual stage, retain inspectable run history, handle four prepared edge cases deliberately, and present it in a distinctive, polished interface.

**Architecture:** Keep the existing invitation-first vendor, processing, validation, exception, reviewer, and procurement domain. Add a PS-2-oriented run-history surface over the existing `ValidationRun` records, and present existing processing stages and decision evidence in a coherent run detail. Improve the role dashboards and decision workspace with shared visual rules; do not build a second shadow workflow or pretend simulated checks are authoritative.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS v4, Lucide; FastAPI, SQLAlchemy, Pydantic; existing Pytest and Playwright acceptance infrastructure.

**Spec:** `ASA Case Study — Candidate Guide.pdf`, especially pages 1–2, 4 and 6–7. The PS-2 requirements in that guide take precedence for evaluator scope. `Final_Consolidated_Product_Specification_Vendor_Onboarding_Platform.docx` supplies implementation detail where it does not expand or conflict with the assignment.

## Case-study requirements (source of truth)

- Take a vendor submission as input and produce a reasoned status: approved, pending, or rejected.
- Communicate what is needed for any non-approved outcome.
- Execute the process on real input; do not substitute a mockup or a dashboard that only simulates execution.
- Show each process stage while it runs and show run history, status, and outputs in a dashboard.
- Include 2–4 realistic, non-trivial edge cases that behave differently from the happy path.
- Supply a live, runnable link and a narrated demo video of no more than five minutes, showing a happy path and at least one edge case.
- Explain decisions to a non-technical buyer; state assumptions when the problem is ambiguous.

## Global constraints

- Keep external registry results labelled as simulated; do not claim live government or bank integrations.
- Synthetic vendor documents and identifiers only in the public demo.
- Approval remains human-controlled and blocked by known unresolved material conflicts.
- Unknown, unreadable, and unavailable remain distinct from negative verification.
- Prioritise one fully working, coherent workflow over adding breadth.
- Avoid changes to deployment cost or persistence tier; the public Render service stays free and temporary.
- The interview demo is capped at five minutes and must include an actual execution.

## Review focus

1. A new vendor can enter realistic information and submit it through the ordinary process; verify a fresh invite-to-submit browser journey.
2. A clean submission receives a reasoned approval-eligible result; bank conflict produces a visible block and vendor action; rerunning corrected evidence updates dependent findings.
3. Unreadable evidence, wrong-slot proof, and unavailable external provider produce distinct states with distinct owners and next steps.
4. The existing upload stages reflect persisted processing state; saved validation findings and the resulting status are available after submission and refresh. Do not imply that a human review is currently running when only its pending state is known.
5. The reviewer action group, forms, tables, and mobile vendor correction remain aligned and usable at laptop, screen-share, and phone widths.

---

## Proposed PS-specific grading metric (100 points)

This is a diagnostic score built from the candidate guide, not an official Zamp grading scale. Maximum points require observable evidence, not just code or a polished screenshot.

| Dimension | Points | Evidence required |
|---|---:|---|
| Live, end-to-end input-to-output execution | 24 | Fresh realistic vendor input and proof run through the actual process; output status is saved and reasoned; non-approved outcome includes useful next action; repeat execution is consistent. |
| Decision quality and safe outcomes | 20 | Clean case can proceed to human approval; material inconsistency blocks; rejected/pending/unknown outcomes are distinguished and explained; no known blocker is approved. |
| Deliberate edge-case handling | 16 | Four prepared cases (conflicting bank evidence, wrong document type or unreadable proof, unavailable registry, and a constitution-dependent checklist case) each produce a different expected treatment and clear explanation. |
| Live run visibility | 15 | Real stages are visible while executing; user can see completion/failure and the output; stage labels and errors are understandable. |
| Run dashboard and inspection | 10 | History is present with status and outcome; a specific run can be opened to inspect input, findings, and decision; useful filtering/empty/loading states. |
| UI/UX, language, and presentability | 8 | Primary actions are obvious and aligned; role screens are coherent; vendor instructions are human-readable; layout remains legible at desktop and mobile sizes; controls do not appear crooked or inconsistent. |
| Product and consulting judgment | 4 | Workflow map, rule choices, assumptions, limitations, buyer impact and an appropriate success/guardrail metric are explained accurately. |
| Five-minute demo readiness | 3 | Rehearsed <=5-minute story shows a live happy path and an edge case, explains the decision and is honest about simulations/limits. |
| **Total** | **100** | |

Score each evidence line full / half / zero / untested. Unknowns remain a range. Hard readiness gates: live fresh submission, zero known-blocker approvals in the prepared test set, and a five-minute-or-shorter run showing happy path plus an edge case. A high numeric score cannot override a failed gate.

## Implementation file map

- `backend/app/api/endpoints/validation.py` and `backend/app/schemas/validation.py`: organisation-scoped validation-run history and exact-run detail endpoints and response shapes.
- `frontend/src/api/validation.ts` and `frontend/src/types/validation.ts`: typed list and detail access for saved validation executions.
- `frontend/src/components/views/ProcurementDashboard.tsx` and `frontend/src/components/runs/ProcessRunHistory.tsx`: a first-class run-history view and exact-run inspection panel without duplicating the application queue.
- `frontend/src/components/review/ApplicationDetailsWorkspace.tsx`: align decision controls and expose compact process/run summary.
- `frontend/src/components/vendor/SubmissionConfirmation.tsx`: show saved validation counts instead of implying that a generic live human review is underway; state the next owner and decision path plainly.
- `frontend/src/index.css`, shared UI primitives, and affected screen files: deliberate visual system and alignment fixes.
- Existing backend unit and browser acceptance tests plus focused history, tenant-scope, exact-run, notification-count, and result-copy coverage.
- `PROTOTYPE_GRADING_RUBRIC.md`, `PROTOTYPE_GRADE.md`, `DEMO_SCRIPT.md`, and `DEMO_RUNBOOK.md`: update to PS-specific assessment and a <=5-minute live narrative.

## Execution tasks

### Task 1 — Baseline against the original problem statement

- Record the current UI and workflow in a fresh local browser run at 1440×900 and 390px.
- Run the existing backend and frontend suites; save full outputs with the plan ledger.
- Execute the happy path and each prepared edge case with expected outcomes written before each run.
- Grade every PS-specific check; record exact evidence and unknowns in `PROTOTYPE_GRADE.md`.
- Treat the previous 100-point prototype rubric score as historical; do not translate it mechanically.

### Task 2 — Make the real process inspectable as runs

- Add tenant-scoped history and exact-run detail endpoints over saved validation runs, newest first, including application reference/vendor, created time, run type, result counts, and current case outcome/reason.
- Add a typed client and dashboard history view with loading, empty, error, and populated states.
- Open the selected saved run's own findings and recommendation; provide a separate link to the current application and accurately label simulated-provider checks.
- Add tests for tenant isolation, deterministic ordering, mixed statuses, exact-run findings, and no cross-tenant disclosure.

### Task 3 — Clarify the live process and outcomes

- Preserve and verify the existing five actual upload-processing stages: file transfer, text reading, document identification, detail extraction, and result check.
- Display saved validation counts on the vendor result screen and remove copy that incorrectly claims a generic live review is underway.
- Keep approved, pending/action-required, rejected, and unavailable/unknown distinct, with the next owner and action stated accurately.
- Ensure approved, pending/action-required, rejected, and unavailable/unknown cases render distinct reason and next-step content.
- Add tests that assert state-to-copy mapping and real run result consistency.

### Task 4 — Rework the UI for confident operational use

- Establish shared spacing, type scale, color roles, action hierarchy, button heights, alignment, and status presentation.
- Fix the reviewer decision group that currently wraps the approval control onto a separate misaligned row.
- Improve procurement/reviewer hierarchy so current work and next action lead; retain deep technical evidence behind the relevant case detail.
- Make the vendor correction path short, reassuring, and mobile-first; keep reviewer evidence comparison desktop-first.
- Add responsive/browser checks for decision-action alignment, horizontal overflow, keyboard focus and primary task discoverability.

### Task 5 — Lock the four demonstrable edge cases

- Use the existing scenario workbook; verify one happy path plus four non-trivial cases (bank mismatch, unreadable/wrong-slot proof, provider unavailable, conditional-document variation).
- Keep each scenario's expected result and owner/next action explicit; run through ordinary UI wherever possible.
- Add or repair regression checks for any failure found; do not add cases merely to inflate volume.

### Task 6 — Regrade, rehearse, publish-ready review

- Re-run all relevant tests and the fresh browser flow; inspect screenshots at desktop and phone dimensions.
- Re-score the PS-specific rubric check by check, preserve unknowns, and verify hard gates.
- Rewrite the demo script to fit five minutes, include one live happy path and one edge case, and distinguish real from simulated behavior.
- Confirm the free hosted URL health and first-load behavior; update hosting notes only if observed behavior changes.
- Finish with a final whole-change review and one prioritized fix pass for any critical or major PS gap.

## Score loop

After every meaningful iteration: (1) run the narrow failing test first, (2) verify it fails for the intended reason, (3) implement one coherent change, (4) run targeted plus regression checks, (5) update only affected rubric evidence and rescore, (6) inspect the rendered screen. Stop when every PS-specific evidence check is demonstrated and the readiness gates pass, or record the highest remaining gap as externally untestable (for example, genuine first-time-user comprehension without access to participants).
