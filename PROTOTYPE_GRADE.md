# Zamp PS-2 prototype grade

**Current local build · 9 November 2026 · PS-specific rubric v2.0**

## Current result: 92.8–95.0 / 100

This is an evidence-based internal diagnostic, not Zamp's official score. Evidence is assessed for 96.5 of the 100 weighted points. The remaining 3.5 points are untested: first-time-user/accessibility evidence and a timed, narrated audience demonstration. The lower bound gives those unknowns zero; the upper bound gives them full marks. The public Render URL is reachable and its health endpoint returns HTTP 200, but the published service still needs to redeploy this local build. It is not honest to call the product perfect or award the maximum while those evidence gaps remain.

| Dimension | Result | Evidence and remaining gap |
|---|---:|---|
| A. End-to-end working process | **24/24** | Fresh browser submission, refresh persistence, reviewer approval HTTP 200, vendor result and staff queue consistency, 15 findings, and a visible real document-reading stage: [fresh run results](testdata/fresh_browser_results.json). |
| B. Decision quality and safety | **20/20** | The scenario runner matched expected checks/outcomes across the prepared cases, including wrong and matching bank corrections, approval blocking, PAN/GST identity conflicts, unreadable evidence and rejection: [scenario results](testdata/scenario_results.json). Synthetic results demonstrate behavior on these fixtures only, not real-world accuracy. |
| C. Edge-case coverage | **16/16** | Fourteen case IDs cover company, proprietor, partnership and LLP variations, with 15 recorded result entries because V03 includes a correction sequence. All recorded assertions passed. See [dataset](testdata/vendor_scenario_dataset.xlsx) and [results](testdata/scenario_results.json). |
| D. Live process visibility | **11.25/15** | Actual upload stages and a live document-reading state are visible. The saved validation run can be inspected. The product does not show each business validation check progressing live as its own stage; the exact-run panel is primarily a post-run view. |
| E. Run dashboard and inspection | **10/10** | Staff can open Processing Runs, see recent status/counts/reasons, inspect that run's persisted findings and follow a separate link to the current case. API tests cover ordering and tenant boundaries; the local screen was inspected. |
| F. UI, language and presentability | **6–8/8** | Current browser checks show aligned reviewer controls, distinct hierarchy, clear correction/rejection text, and no mobile horizontal overflow at 390px: [UI results](testdata/ui_results.json). Keyboard-only completion, measured contrast and independent first-time comprehension remain untested (F4 = U). |
| G. Product and consulting judgment | **4/4** | [Decision note](CASE_STUDY_DECISION_NOTE.md) states user/handoff, scope choice, a time-to-decision outcome, safety and counter-metrics, pilot plan, assumptions and a sensitivity-based capacity hypothesis. The numbers are identified as assumptions, not product results. |
| H. Five-minute demonstration | **1.5–3/3** | The public evaluator URL and health endpoint are reachable, and an honest timed script is prepared. No timed narrated rehearsal, recording, or independent viewer-recall observation is evidenced (H2/H3 = U). |
| **Total** | **92.8–95.0/100** | The range preserves the 3.5 untested points; exact pre-round range is 92.75–95.0. |

## Readiness gates

1. **Fresh ordinary-UI submission with a saved, reasoned result: demonstrated locally.**
2. **At least two distinct edge cases behave as specified, with no known blocker approved: demonstrated on the prepared synthetic set.**
3. **Non-approved result explains the reason and action/owner: demonstrated in browser and scenario checks.**
4. **Evaluator-accessible runnable URL plus a narrated demo within five minutes showing happy path and edge: URL/health demonstrated; narrated demo still unverified.**

The first three gates pass on current local evidence. Gate 4 remains open; therefore the project is not yet submission-ready even though the product score is high.

## Exact checks behind the score

| ID | Mark | Evidence |
|---|---:|---|
| A1–A4 | 1, 1, 1, 1 | Fresh UI path, process submission, refresh persistence and cross-role consistency in `testdata/fresh_browser_results.json`. |
| B1–B4 | 1, 1, 1, 1 | Clean human approval path plus V03 correction, unavailable provider, unreadable evidence and material conflicts in `testdata/scenario_results.json`; reviewer decision browser run. |
| C1–C4 | 1, 1, 1, 1 | Bank conflict, wrong-slot/unreadable proof, provider/identity edge and constitution-dependent cases across 14 case IDs. |
| D1–D4 | 1, 1, 1, 0 | Actual document-stage UI and outcome; no live step-by-step progress sequence for business validation itself. |
| E1–E4 | 1, 1, 1, 1 | History table, exact-run panel, current outcome/reason and simulation disclosure; endpoint tests cover tenant scope. |
| F1–F4 | 1, 1, 1, U | Alignment, hierarchy and 390px behavior verified; accessibility and independent comprehension untested. |
| G1–G4 | 1, 1, 1, 1 | `CASE_STUDY_DECISION_NOTE.md`. |
| H1–H4 | 1, U, U, 1 | Public URL and `/api/health` return HTTP 200; script ready; no timed rehearsal/audience recall evidence; accurate simulation/limitation language. |

## Highest-value next steps

1. Push the tested local build and wait for Render to publish it; verify the revised screen and health endpoint from a clean browser.
2. Record a narrated, timed run of the prepared happy path and one edge case; check it stays under five minutes and ask a viewer who has not seen the project to explain what happened.
3. Run a brief first-time vendor task and a keyboard pass. Measure contrast and document findings rather than infer accessibility from appearance.

Only repeat the score after the evidence above exists. The UI browser check does not substitute for a human usability session, and scenario-set success is not a production error-rate claim.
