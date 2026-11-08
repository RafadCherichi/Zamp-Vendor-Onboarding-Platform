# Maximum Score and Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the Zamp PS-2 prototype from the evidence-backed 72.8–84.8/100 range toward 100/100, then give evaluators a dependable runnable link and a narrated demonstration under five minutes.

**Architecture:** Keep the existing React/Vite frontend and FastAPI backend. Build one production image that serves the frontend and `/api` from one origin. For the time-boxed synthetic demonstration, use one paid Render web-service instance with a persistent disk for SQLite and uploaded files; keep one process/worker, and initialise demo data only when the database is empty. GitHub stores the reviewed source and triggers deployment. This is a proposal for a reliable case-study submission, not a claim that the current build is ready for public traffic.

**Tech Stack:** React 19, TypeScript, Vite 8, FastAPI, SQLAlchemy, Alembic, SQLite, Docker, GitHub, Render, Playwright or existing browser acceptance scripts, pytest, oxlint.

**Spec:** [Approved rubric](../../../PROTOTYPE_GRADING_RUBRIC.md), [iteration 2 grade](../../../ITERATION_2_GRADE.md), [case-study decision note](../../../CASE_STUDY_DECISION_NOTE.md), and `ASA Case Study — Candidate Guide.pdf` in the repository root.

## Score target and honest limit

The current exact range is **72.75–84.75/100**, with **88/100 points assessed**. The missing lower-bound points are A3 +2.5, C2–C4 +4.5, E3 +1.25, F +8.75, G +6.25, and H +4.0. The arithmetic describes the possible score under this rubric; it is not a promise. Full marks require observed independent comprehension and accessibility, a public working process, and a real narrated recording. No screenshot or passing unit test can substitute for those observations.

The candidate guide sets two submission gates apart from the numerical score: an evaluator-accessible runnable link and a video of five minutes or less that shows a live happy path plus at least one deliberately designed edge case. The video must explain what happened and why. The 16.5-second silent rehearsal is evidence for iteration, not the final submission video.

## Global Constraints

- Use **synthetic data only** in the public evaluation service; never upload actual PAN, bank, GST, or personal documents.
- Keep the decision policy that a material conflict cannot silently become approved. Preserve the distinction among bad evidence, uncertain extraction, and a simulated registry outage.
- Mark simulated or inferred verification as such at the point of use. Do not imply an official registry was queried unless it really was.
- Keep the approved rubric unchanged while improving the product. Record evidence for each of A1–H4 as `mark | expected | observed | evidence | grader`.
- Keep the public demo recoverable without allowing anonymous users to destroy the shared dataset. A reset must be restricted to an authorised admin or to an authenticated deployment operation.
- Use one origin so invitation links, cookies or bearer requests, and document previews work without an additional cross-origin setup.
- Preserve database and uploaded files across restarts and deploys; a seed routine must not delete an existing case.
- Treat the 14-row spreadsheet as a regression set. Showcase only two to four deliberate edge cases to the evaluators.
- A change is complete only after the relevant automated check and a browser observation on the running build pass. Record the exact build and test results.

## Review Focus

1. A visitor can call `/api/demo/reset` without a token today. After the fix, anonymous and non-admin calls must fail; an authorised admin operation must work.
2. Startup or redeploy can invoke a destructive seed today. After the fix, a previously submitted case, its document and decision must survive restart and deployment.
3. An invitation's `/invite/<token>` path must load directly on the public URL, including browser refresh.
4. A delayed extraction or failed verification must show an accurate stage and owner, never a fabricated success or an endless spinner.
5. A synthetic document preview and a correction after a rejected decision must be readable and scoped to the right role and case.

## File map for implementation

| Area | Existing files to inspect or modify | New focused files likely needed |
|---|---|---|
| Public safety | `backend/app/api/endpoints/demo.py`, `backend/app/core/deps.py`, `backend/app/config.py`, `backend/app/db/seed_demo.py`, `backend/app/storage/local.py` | `backend/tests/test_public_demo_safety.py`, a non-destructive initialisation module |
| One-link deployment | `backend/app/main.py`, `backend/app/api/endpoints/health.py`, `frontend/.env.example`, `.gitignore` | root `Dockerfile`, `.dockerignore`, `render.yaml` only if its settings match the chosen Render service, `backend/tests/test_served_frontend.py` |
| Live run | `backend/app/services/extraction/pipeline.py`, `backend/app/api/endpoints/applications.py`, `frontend/src/components/vendor/OnboardingWizard.tsx` | a processing-status schema/endpoint or event model and a small status component |
| Reviewer evidence | `frontend/src/components/review/ApplicationDetailsWorkspace.tsx`, `frontend/src/components/queue/ApplicationQueue.tsx`, `backend/app/schemas/application.py` | focused submitted/extracted/provenance component and browser check |
| Language and presentation | vendor status/correction components, `frontend/src/index.css` | task script, observation sheet, contrast/keyboard evidence |
| Submission proof | `DEMO_SCRIPT.md`, `DEMO_RUNBOOK.md`, `ITERATION_2_GRADE.md` | final grade, public smoke log, recording link and evaluator handoff note |

---

## Phase 0 — Freeze the baseline and prepare a safe source snapshot

### Task 0.1: Record exactly what exists

- [ ] Save `git status --short`, current commit, branch and `git remote -v` in the work log. At plan time the branch is `master`, the remote list is empty, and many earlier improvements are uncommitted; do not claim that GitHub already contains this version.
- [ ] Open the 14-case workbook and the expected/observed results. Preserve the prewritten expectations and identify which cases run through the full UI versus API checks.
- [ ] Keep a backup of local SQLite and uploads before changing reset, migration, or storage logic. Keep that backup outside the public repository.
- [ ] Review tracked and untracked content for real customer data, secrets, large generated artifacts and unneeded videos. `.env` files and SQLite databases are ignored, but inspect staged changes before every push.
- [ ] Re-run the existing baseline checks and record exact counts. Current documented evidence says 97 backend tests passed, frontend build/lint passed, and 14/14 synthetic scenario rows matched.

**Exit:** Reproducible baseline, clean understanding of what will be published, no accidental secret or private-data commit.

## Phase 1 — Make a public synthetic demo safe and durable

### Task 1.1: Restrict destructive reset and production configuration

- [ ] Add tests proving an anonymous `POST /api/demo/reset` and a logged-in non-admin request cannot reset data; the authorised admin can reset only in the dedicated demo environment. Test the data remains unchanged on denial.
- [ ] Change `backend/app/api/endpoints/demo.py` to require the project’s existing auth and admin-role dependency. Remove the raw exception text from its public 500 response, while preserving detailed server logs.
- [ ] Require a non-default `SECRET_KEY` when `ENVIRONMENT=production`; set `DEBUG=False` in the hosted service. Decide whether to disable public API docs there.
- [ ] Remove the silent storage fallback in `backend/app/storage/local.py`: unsupported storage choices must fail at startup rather than pretending remote storage is active.
- [ ] Run the targeted security tests and existing auth tests. Review the public routes for other state-changing operations without the intended role checks.

**Exit:** Public users cannot erase or impersonate the demo; the app cannot start in production with a known development secret.

### Task 1.2: Initialise data without destroying submissions

- [ ] Write a test that creates a submitted case and file, runs startup twice, and confirms the same case, file and decision survive.
- [ ] Add a non-destructive `initialise_demo_if_empty` operation distinct from `reset_and_seed_demo`. Keep the latter behind the authorised reset route for rehearsal only.
- [ ] Run Alembic migrations on service startup or through an explicit deploy step that has access to the runtime disk. Seed a few labelled synthetic demo accounts/cases only if the database is genuinely empty.
- [ ] Point SQLite and uploads at a persistent mount such as `/var/data/vendor_onboarding.db` and `/var/data/uploads`. Use one worker with SQLite. Prove a restart and a redeploy retain both data and file previews.

**Exit:** The evaluator’s cases remain available after idle periods and updates.

## Phase 2 — Build the one-link public app

### Task 2.1: Serve the built frontend from FastAPI

- [ ] Add tests for `GET /`, `GET /invite/<token>`, browser refresh on that path, static assets, `GET /api/health`, and unknown `/api/...` returning a genuine API 404 instead of the React shell.
- [ ] Build React with `VITE_API_BASE_URL=/api`; serve `frontend/dist` from FastAPI for non-API paths. Preserve its existing API router and document preview routes.
- [ ] Add a root multi-stage `Dockerfile`: Node builds the frontend; Python installs backend dependencies and runs Uvicorn on `0.0.0.0:$PORT`. Keep generated files, virtual environments, local databases and secrets out of the image with `.dockerignore`.
- [ ] Run the container locally against a disposable data directory and complete login, invitation direct-link, upload, decision, correction and refresh in a real browser.

**Exit:** One URL opens both UI and API; direct links and uploads work.

### Task 2.2: Add an honest public health check

- [ ] Test the health endpoint with a working and a broken database. A degraded dependency must be machine-detectable, preferably a non-2xx response on the health-check path.
- [ ] Preserve a readable diagnostic body for the operator while ensuring secrets are absent.
- [ ] Use that endpoint for the host health check, and add an end-to-end smoke test that inspects the body as well as status.

**Exit:** The host cannot call the app healthy when its core database is unavailable.

## Phase 3 — Make execution visibly truthful (A3, +2.5)

### Task 3.1: Expose real processing state

- [ ] Define the smallest stage record needed: case/reference, document or check, stage (`queued`, `reading`, `checking`, `needs_review`, `complete`, `failed`), timestamp, and human-readable next owner. Derive it from actual work, not a timer.
- [ ] Test a deliberately delayed extraction, failed reading, and simulated registry timeout. Assert the API emits the right intermediate and final states, and never marks a failed stage complete.
- [ ] Add a lightweight status endpoint or event stream and a vendor-facing progress component; polling is adequate if reliable. Display completion and persistent reference after refresh.
- [ ] Browser-test the delayed path at desktop and phone widths. Capture a short recording showing truthful intermediate steps.

**Exit:** A3 gets full credit only after a delayed operation shows accurate intermediate progress and result in the ordinary UI.

## Phase 4 — Give reviewers evidence they can defend (C2–C4, +4.5)

### Task 4.1: Compare submitted value with exact proof

- [ ] Test a bank conflict and a corrected second document version. Assert the reviewer sees the submitted account value, extracted value, document name/version, and a working preview of that version in one view.
- [ ] Add a compact side-by-side comparison to the reviewer workspace, with a clear mismatch label and a path to the underlying evidence.
- [ ] Confirm the UI updates after the corrected document is processed without rewriting the older evidence.

### Task 4.2: Show where every consequential claim came from

- [ ] Tag displayed claims as vendor entered, extracted from proof, rule result, simulated external check, or human decision. Use the existing data where possible; add a small schema field only if needed.
- [ ] Test a registry outage and an ambiguous extraction. A reviewer must distinguish uncertainty from a negative verification result.
- [ ] Browser-check labels at the point where the reviewer takes action, not hidden in a separate technical page.

### Task 4.3: Make queue and history explain the latest state

- [ ] Test the clean, conflict and outage cases for owner, current blocker, last material change, next action and latest decision rationale.
- [ ] Put a concise case summary in the queue and a chronological, readable history in the workspace. Link the decision to the evidence and actor that produced it.
- [ ] Have a fresh reviewer answer “who owns this, what changed, what remains open, why this decision?” from the screens alone.

**Exit:** Each C check is independently demonstrated in a browser, including an older document version and the current one.

## Phase 5 — Complete the buyer recommendation (E3, +1.25)

### Task 5.1: Quantify the cost of acting or waiting

- [ ] Extend `CASE_STUDY_DECISION_NOTE.md` with a small, clearly labelled assumption model: monthly applications, share blocked, staff minutes per clarification, elapsed waiting days, buyer operating consequence, owner of the next action, and low/base/high cases.
- [ ] Separate measured facts from hypotheses. Do not convert elapsed waiting time into staff hours or money without an explicit rate and mechanism.
- [ ] State the recommended action, the cost of unnecessary action, the cost of waiting, and which pilot observations would overturn the recommendation.
- [ ] Ask one nontechnical reader to recount the trade-off; simplify the explanation if they cannot.

**Exit:** E3 has a defensible, unit-labelled decision trade-off rather than only qualitative urgency.

## Phase 6 — Prove the words work for first-time vendors (F, up to +8.75)

### Task 6.1: Run uncoached comprehension sessions

- [ ] Prepare four short tasks in ordinary language: interpret a submitted status; resolve a bank correction; interpret a registry outage; explain task-critical terms such as PAN, GST, authorised signatory, and “verification”.
- [ ] Recruit at least two or three first-time participants if feasible; record whether a colleague is a proxy. Give the goal, do not teach the screen, and record their first answer and first action verbatim.
- [ ] Score F1–F4 against the rubric for each participant before changing the copy. Note hesitations, wrong next owners, and any moderator help.

### Task 6.2: Revise the exact failed language, then repeat

- [ ] Rewrite status and correction copy to answer: what happened, which value or document is at issue, what the vendor does next, and who acts after that. Give registry outages a staff-owned message when no vendor action is needed.
- [ ] Put short examples or help beside terms that participants could not explain. Avoid blame and avoid “verified” where the result is only a format check or simulation.
- [ ] Repeat the same tasks with a new first-time participant; capture completion and paraphrase without hints.
- [ ] Record F marks with participant evidence and limitations. Do not award 1 from the improved copy alone.

**Exit:** Each F check has observed first-time-user evidence and wording that matches the real action.

## Phase 7 — Make the interface feel deliberate and usable (G, up to +6.25)

### Task 7.1: Fix first-glance hierarchy and screen-share legibility

- [ ] Show the current screens for five seconds to fresh viewers. Ask them to point to current status and primary action without a prompt; record misses before revising.
- [ ] Refine the existing restrained visual direction: one clear heading, one dominant next action, consistent type scale, grouped submitted/proof/rule content, generous spacing, restrained accent colour, and plain microcopy. Avoid ornamental AI-style cards or decorative gradients.
- [ ] Inspect the reviewer view at actual presentation screen-share size and the vendor correction view at phone size. Fix small secondary text and dense evidence blocks.
- [ ] Re-run the first-glance and screen-share tasks with fresh viewers and retain screenshots of the final states.

### Task 7.2: Verify task completion on devices and by keyboard

- [ ] Complete the full vendor correction on a 390px phone view and the evidence review/decision on a typical laptop view. Check the action and relevant field remain present after errors and refresh.
- [ ] Traverse login, invitation, upload, correction, evidence and decision by keyboard. Fix missing programmatic labels, focus order and invisible focus indicators in the sampled journey.
- [ ] Measure normal-text contrast to WCAG 2.2 AA 4.5:1 where applicable; use text plus shape/words for status, not colour alone.
- [ ] Run focused automated accessibility checks and a manual keyboard pass. Record the scope of the check; do not claim whole-product accessibility from one path.

**Exit:** G1–G4 each have direct task evidence, measured contrast, and final screenshots.

## Phase 8 — Publish through GitHub and Render (H1 plus submission gate)

### Task 8.1: Create a reviewed GitHub source repository

- [ ] Decide repository owner/name and visibility. A private repository is sufficient if Render has access and evaluators only need the public app and recording; choose public only if source review is required and all tracked material is shareable.
- [ ] Stage files deliberately and inspect `git diff --cached --stat` and `git diff --cached --check`. Do not stage the local database, `.env`, uploaded real documents, or unnecessary heavy video files.
- [ ] Commit the verified baseline and deployment changes on a `codex/...` branch or the desired branch. Create an empty GitHub repository with no generated README, then add it as `origin` and push. Protect the final branch from last-minute untested edits.
- [ ] Confirm the remote repository contains the plan, rubric, dataset or test instructions, runbook and source required to reproduce the app.

### Task 8.2: Deploy one public web service

- [ ] In Render, connect the GitHub repository and create a **Web Service** using the root Dockerfile. Use a paid instance with one attached persistent disk mounted at `/var/data`; do not put SQLite or uploads elsewhere.
- [ ] Set `ENVIRONMENT=production`, `DEBUG=False`, a random `SECRET_KEY`, `DATABASE_URL=sqlite:////var/data/vendor_onboarding.db`, `STORAGE_LOCAL_DIR=/var/data/uploads`, `STORAGE_BACKEND=local`, and any other required non-secret configuration in Render. Supply secrets only through host environment settings.
- [ ] Set the health path to the real health endpoint, enable deployment on reviewed commits, and note the issued `https://...onrender.com` URL.
- [ ] From an incognito browser on another network/device, test login, invitation direct link, fresh submission, upload, preview, blocked approval, correction, decision, vendor status, page refresh and restart persistence.
- [ ] Test that a public visitor cannot reset the service. Record the exact deployed commit, public URL, date, expected/observed actions and screenshots.

**Exit:** The runnable URL is accessible without local software and survives a restart. If the host requires a spending decision, complete the build and local proof first and present the exact service and disk choice before activating billing.

## Phase 9 — Tell the five-minute story (H2–H4 plus submission gate)

### Task 9.1: Rehearse a focused run

- [ ] Update `DEMO_SCRIPT.md` to use only a prepared clean case and one bank mismatch or registry outage, with a short buyer explanation and explicit “simulated” label.
- [ ] Target a 4:30–4:50 rehearsal: problem and buyer (0:00–0:30); vendor input and documents (0:30–1:35); visible processing/result (1:35–2:15); reviewer decision (2:15–3:00); edge, owner and recovery (3:00–4:10); value, trade-off and metric (4:10–4:45).
- [ ] Rehearse on the deployed public URL, not a local shortcut. Ensure the screen is readable at the recording resolution and all promised actions execute.

### Task 9.2: Record and independently check comprehension

- [ ] Make one narrated recording of five minutes or less showing the live process, happy path and at least one edge executing. No slide-only substitute; no secret or personal data on screen.
- [ ] Give the recording to a nontechnical viewer. Ask them what the input was, why the decision happened, who acts next and what the buyer gains. Record their answers; adjust the narration and re-record if the logic is unclear.
- [ ] Store the recording at an evaluator-accessible link and test it in incognito. Add the runnable link, recording link, demo credentials and a short “what is simulated” note to a one-page handoff.
- [ ] Rehearse two follow-up questions: what actually ran versus simulated, and why this design trade-off was made in one week.

**Exit:** Both submission links work, the video is within five minutes, and H3/H4 have witnessed evidence.

## Phase 10 — Regrade, repair and freeze

### Task 10.1: Run the final regression and live evaluation

- [ ] Re-run backend tests, frontend build and lint, the 14-row workbook, and fresh browser cases for clean approval, material conflict, outage, wrong proof, correction and rejected decision.
- [ ] Re-test all eight rubric dimensions on the **deployed** build; record every check A1–H4 with observed evidence and an exact mark. Have a second grader independently mark the ambiguous checks.
- [ ] Keep U visible until actually examined. Recalculate the total using the rubric formula; do not round individual dimensions before summing.
- [ ] Verify the core PS-2 readiness condition and the two separate submission gates. If either fails, fix the highest-buyer-impact failure, repeat its test and regrade affected checks.
- [ ] Freeze the exact deployed commit and recording after a final incognito check. Save the final scorecard and evidence links in a new final-grade document; retain earlier grades for traceability.

**Exit:** A 100/100 claim is allowed only if all 32 checks have demonstrated marks of 1 and both submission gates pass. If observation produces a lower score, report that score and the remaining gap honestly.

## GitHub push: concrete operator sequence

The repository currently has no remote. After Phase 0 review and verified implementation, create an **empty** GitHub repository in the chosen account. In PowerShell, from this project folder:

```powershell
git status --short
git switch -c codex/evaluator-submission
git add -p
git add .\docs\superpowers\plans\2026-11-08-maximum-score-and-publication.md
# Add each other reviewed new file by its explicit path.
git diff --cached --stat
git diff --cached --check
git commit -m "Prepare evaluator-ready vendor onboarding demo"
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin codex/evaluator-submission
```

Replace `OWNER` and `REPOSITORY` with the actual choices. `git add -p` reviews changes to tracked files; add any further **new** files one path at a time after reviewing them. The sequence intentionally avoids `git add .` because this working tree contains many existing modifications. GitHub will ask for normal account authentication if it is not already configured. If the branch or `origin` exists by then, reuse or update it rather than creating a duplicate.

## Why GitHub Pages is not the runtime for this app

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) publishes static files and does not run Python. This prototype's validation, decisions, document processing and persistence live in FastAPI. A Pages-only upload would show a shell whose `/api` calls fail. A separate Pages frontend and hosted API is possible but adds cross-origin configuration, a Vite base path, direct-link fallback and two URLs. The one-origin Render service above is simpler for the evaluators. Render's [FastAPI deployment guide](https://render.com/docs/deploy-fastapi) explains the GitHub connection and public URL. Its [free-service documentation](https://render.com/docs/free) says free instances spin down after inactivity and lose local SQLite/uploads on restart or redeploy; [persistent disks](https://render.com/docs/disks) require a paid service. That is why the plan specifies a paid disk or, if cost must be avoided, a separately engineered persistent database and object store before publishing.
