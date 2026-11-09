# Implementation checkpoint — 9 November 2026

Approved scope: prototype-audit-2026-11-09.md. Changes remain local and uncommitted; hosted demo has not been updated.

## Current checkpoint — resumed, conserving remaining usage

This section supersedes the historical pause and older test totals below.

- Readiness queries now batch request-local evidence. Local minimal 500-case benchmark: 6 queries / 56.2 ms for Ready, versus 2,542 queries / 1,873.6 ms before. This is not a hosted SLA. Approval still evaluates the authoritative gate separately.
- Final review found and repaired two additional issues: combined replacement-proof + field responses now retain both changes and run one revalidation; unreadable PAN proof now blocks approval and creates an actionable issue. Explicit manual dispositions remain tied to exact findings.
- Regression tests first reproduced both defects. Combined-response integration passes in both field-only and field-plus-proof modes before the PAN hardening; final full-suite rerun is in progress in `backend/.verify_portal_20261109/release_regression_final.log`. A prior full run passed 154 tests; do not substitute that for the post-hardening result.
- Production frontend build passes. Isolated browser checks: 9 passed after the combined-response UI change. Lint exits successfully with existing warnings; not warning-free. Current source adds PAN evidence version links after the latest UI check.
- Eight narrated recording scenes executed successfully, including a fresh UI submission, assigned reviewer approval, vendor approval notice, and correction visibility. Export failed because video.path was called after Playwright closed. Script corrected, but final MP4 has not yet been generated; raw silent recordings are ignored. Narration generation is reproducible with testdata/generate_narration.ps1 and optional tools in testdata/requirements-tools.txt.
- Remaining release work: confirm final regression outcome; refresh scenario/workbook if PAN changes alter outcomes; export and inspect narrated video; update grade with honest usability unknowns; commit, push and verify free Render deployment. No new deployment or perfect-score claim yet.
- User reported 7% usage remaining. Keep further work targeted; avoid new broad research or repeated full audits.

Final result for this pass: **158 backend tests passed**, 1 warning, 63.37 seconds; 9 isolated browser checks passed; frontend production build passed; git diff whitespace check passed. The PAN source-document/version metadata addition was made during the full run; its specific linkage should be included in the next focused browser/evidence refresh. All changes remain local and uncommitted.

## Release status — 9 November 2026

- Scenario manifest refreshed against the release: 14 case IDs, 15 outcomes including the correction sequence, all passed. Workbook refreshed from current manifest/results using the bundled spreadsheet runtime.
- Latest isolated browser suite: 9/9 passed at 320, 767, 768 and 1440 widths, including reviewer access, admin/procurement queue, protected document, exact notification focus/reload and company-matched autofill/reset.
- Commit `2be8ede` was pushed to GitHub `main`, the branch configured in Render. Render health is HTTP 200. Its deployed JavaScript SHA-256 matches the local release bundle exactly.
- Hosted reviewer queue smoke check returned 3/3 currently assigned cases: clean case ready; correction and registry-risk cases blocked. No decision or data changes were made by the hosted smoke check.
- Remaining work: the demo video only (per user request) and later top-level folder organization (user requested defer until project is finished). Narrated recording export has not yet succeeded.
- All release changes are committed. Working tree was clean at push; generated workbook inspect output is ignored.

## Completed changes with focused verification
- One responsive case collection; queue response preserves blocker/reply fields; stale search responses discarded.
- Existing invite acceptance verifies current password and preserves credentials; incompatible membership rejected.
- Decision authority requires assigned reviewer/admin; terminal decision states protected; all failed findings checked; dispositions bound to exact finding; incomplete/stale runs block approval.
- Vendor corrections limited to owner and requested field; checklist uploads constrained and bounded; document response sent once with explanation; repeated version link idempotent; other unanswered requests preserve ACTION_REQUIRED.
- Draft saves sequenced, reset waits for saves, Next stays on failed save.
- Dashboard overdue/completion/unassigned cohorts added; high priority includes HIGH and CRITICAL; decorative admin cards and numbers removed.
- Notification destinations stored in URL, restored after login/reload and browser history; exact request focus added; escalation refresh enabled; notification failure visible.
- Validation task creation and completed current run published in one transaction; submission processing failure creates explicit FAILED result; escalation notification argument corrected.

## Latest checks
Production frontend build passes. 65 focused backend tests pass, including the injected validation-task-failure regression. Tests use backend/.verify_portal_20261109/visual_release.db, a synthetic database. Legacy tests now use the approved assignment policy, current upload slots and independent fixture identifiers. Full-suite verification is recorded below.

## Reviewer assignment addition
Implemented reviewer-only assignment scoping for queues, dashboard metrics/activity, case details, validation history, exceptions, comments, document access via shared guard and case notifications. Two-reviewer HTTP regression verifies filter tampering, unassigned denial, organisation staff access and immediate reassignment revocation. No Chrome access in this batch.

## Document and verification batch
Private previews now fetch files with Authorization headers and display revocable browser object URLs. Query bearer tokens are rejected. Exact-version preview regression passes. Generic PAN/GST/MCA/bank verification fallbacks removed; fixture records no longer echo applicant names. Unknown external verifications block approval. Case overview returns permitted actions and UI disables unavailable decisions. Extraction provider attribution records actual local fallback. Production build and 59 focused tests pass. Chrome not accessed.

## Reset, history and decision concurrency batch
Autofill eligibility is returned by the server from seeded application/vendor/account identities, rather than editable legal name. Baseline reset restores original empty PAN. Run history now shows saved check outcome separately from latest human decision/stage and decision date. Decisions use an atomic status/owner/timestamp comparison; stale writes return 409, including a same-status update. Two independent database sessions verify first winner preservation. Production frontend build passes and 65 focused backend tests pass. Browser not accessed.

## Native Chrome verification and receipt batch
Warned user before controlling the exact existing Chrome prototype window. On local candidate http://127.0.0.1:8016 using isolated browser_candidate_01.db: reviewer shows three visible assigned case cards and three Open case buttons; unassigned baseline excluded. Opened clean Tata case, recorded synthetic approval, signed out and signed in as its vendor. Vendor sees APPROVED receipt, receives one approval notice and opening it sets persistent application URL. This confirms local laptop queue visibility and approval delivery; hosted app unchanged. Added vendor decision date/no remaining tasks and timezone-aware response serialization after noticing naive timestamps in UI. Latest frontend build passes; 64 focused tests plus 3 updated legacy preview tests pass. Timestamp/receipt additions still need browser verification.

Browser observations have been addressed in the fixture batch below; new fixtures still need a browser pass.

## Consistent demo fixtures and full correction journey
Apex practice autofill now has independent PAN, bank and Udyam fixture identities; regenerated the actual public PDFs to match. Sharma has its required establishment proof and a distinct corrected bank fixture (60200012345678), with seeded question text updated. Logistics has matching PAN, bank, LLP, authority and transport proof; AAA-1234 produces an actual simulated MCA timeout and reuses its generated issue. The designated duplicate concern is labelled as seeded, not a measured similarity. Isolated integration test uses shipped frontend autofill values/PDFs to submit cleanly, then answers two Sharma requests separately, proves reviewer reply visibility and blocked interim approval, resolves both and verifies vendor receives final approval. 65 focused backend tests and production frontend build pass. No Chrome access in this batch. No hosted data reset or deployment.

## Full-suite and final server safeguards
Full backend suite passed 151 tests before the final upload reservation change. Its targeted post-change checks passed 32 tests. Final full run is in progress (full_release_final.log). Invitations use an atomic pending-to-accepted claim; two-session test confirms only one acceptance succeeds. Dashboard processing counts active jobs rather than optional empty slots. Uploads reserve a new current version atomically before allocating the number, and reject competing stale uploads with 409; targeted evidence/round-trip checks pass. Updated legacy scenario setup to assign reviewers and use current synthetic identifiers. Fresh browser preview for the next UI pass is at http://127.0.0.1:8017, isolated browser_candidate_02.db. Warned user before planned native Chrome access.

## Latest verified release state
Full backend suite: 153 passed, one pytest configuration deprecation warning (full_release_pan_corrected.log). Production frontend build passes. Native Chrome on isolated preview 8017 verified admin four visible cases; high-priority count three issues opens two correct cases; procurement four cases and Being completed filter; procurement case view has no decision buttons; vendor corrects bank number through UI; reviewer sees Vendor replied on its case card. Browser control ended and user informed Chrome is free.

Post-browser fixes: stage clicks scroll to queue, procurement decorative numbers removed and Waiting for vendor renamed, vendor exception references hidden, drafts labelled Draft without approval-blocked callout, actual reply/value changes displayed on case entry. These UI changes build but still require a final browser pass. Found and corrected real PAN validator error: LLP requires F, while L is Local Authority, verified against https://www.incometaxindia.gov.in/en/llp . Logistics fixture and PDF now use AABFA1234F; isolated regression asserts no incidental FAILED finding. Browser scripts now use bundled/default or installed Chrome via portable helper; compile checks pass, updated flows are not yet executed.

## Required remaining work
1. Final browser pass for post-browser presentation changes, private previews, notification Back/reload/exact focus, autofill/reset, 320px/reduced motion/200% zoom and keyboard controls. Warn before native Chrome access.
2. Refresh legacy UI/recording assertions, run scenario manifest and update workbook/results with the new build. Workbook still has old LLP PAN AAALE1234F; source JSON is corrected. Current Python lacks openpyxl; use bundled spreadsheet dependencies or install project test tooling when regenerating.
3. Measure queue queries/latency at representative case counts; resolve concrete performance failures only. Record unavailable independent first-time-user usability evidence honestly.
4. Create final rubric assessment and <=5-minute narrated demo from actual release, preserving unknowns and free-hosting persistence limits.
5. Review/stage only intended source/tests/synthetic PDFs/docs; exclude backend/.verify_portal_*/ and local databases. Commit/push to intended GitHub branch, reconcile Render main branch configuration, verify hosted build and two journeys. Hosted app still unchanged.

## User preference
Give a clear warning and time to pause BEFORE taking control of Chrome. Avoid native Chrome access while user is working. No automatic restart can be promised after usage limits stop a session; resume from this checkpoint when user says continue.

## Paused by user
User explicitly requested stop; do not resume until instructed. Latest scenario refresh: 14 cases plus correction retry passed; workbook updated through bundled spreadsheet runtime with no unintended value/formula changes. Isolated UI checks: nine passed, including 320/767/768/1440 case visibility, private preview, exact notification focus/reload, autofill/reset. Mobile receipt badge wrapping fixed and checked again. Narration segments generated; recording was in progress and cancelled at user's request, so do not claim final video exists or is complete. A final-save-before-submit hook was just added and remains unbuilt/untested. All edits remain local; deployment not performed. Recheck recording/process output and latest hook on resume.
