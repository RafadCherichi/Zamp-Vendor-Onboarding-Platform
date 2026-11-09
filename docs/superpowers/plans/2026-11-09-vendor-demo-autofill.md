# Vendor Demo Autofill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a demo vendor populate the entire draft and upload matching synthetic evidence with one action.

**Architecture:** Keep autofill in the vendor wizard. A small scenario module will define fictional profiles and the public demo-file mapping; the wizard will save through the existing draft API, refresh the checklist, upload the selected files through the existing document API, and refresh the displayed application. Nothing is auto-submitted or auto-approved.

**Tech Stack:** React, TypeScript, Vite, existing FastAPI application and document endpoints, existing Playwright verification harness.

**Spec:** `docs/superpowers/plans/2026-11-09-ps2-live-process-and-presentation.md`, particularly live input, normal process stages, synthetic-only public demo, and human-controlled decision requirements.

## Global Constraints

- Use fictional profiles and synthetic documents only.
- Use existing normal draft and upload APIs; do not bypass processing.
- Leave declarations for the vendor to confirm and keep submission manual.
- Do not change hosting tier or persistence.
- Clearly label demo information as fictional and editable.

## Review Focus

- A repeated click does not create confusing duplicate records; upload endpoints create document versions.
- Dynamic checklist slots reflect the selected constitution and registration choices before files upload.
- Upload failure remains visible and does not claim autofill succeeded.
- Consent declarations stay unchecked and submission stays manual.
- Small-screen button layout stays within viewport.

---

### Task 1: Scenario fixtures and red UI verification

**Files:**
- Create: `frontend/src/components/vendor/demoAutofill.ts`
- Modify: `testdata/verify_ui.py`

**Interfaces:**
- Export fictional profile data as typed `ApplicationDraftUpdate` records and mappings from checklist document type to public sample filename.

- [x] Add a Playwright check for the vendor base draft that finds a demo autofill action, runs it, and asserts business, tax, contact, banking, and uploaded mandatory evidence appear while declarations remain unchecked.
- [x] Run the check against the current build; confirm it fails because the action is not present.
- [x] Add the typed scenario fixtures and documented demo file mapping.

### Task 2: One-click draft population

**Files:**
- Modify: `frontend/src/components/vendor/OnboardingWizard.tsx`
- Create: `frontend/public/demo-documents/` (copy only referenced synthetic files)

**Interfaces:**
- Use existing `apiUpdateApplicationDraft`, `apiFetchChecklist`, and `apiUploadDocument`.
- Add one asynchronous handler with progress/error state; after profile save, fetch the updated checklist, upload matching files, then refresh the application into local wizard state.

- [x] Add a clearly labelled “Fill with demo data” action on the Business step with copy that explains the records are fictional and editable.
- [x] On click, save the chosen profile while preserving all three declaration values as false; never submit the application.
- [x] Upload sample documents for the mandatory checklist slots and show completion or the precise failed step.
- [x] Refresh the draft, retain the user on the Business step, and clear stale validation errors.
- [x] Build the frontend and run the focused Playwright scenario and complete existing verification suite.

### Task 3: Ship and verify

**Files:**
- Modify: `DEMO_SETUP.md`

- [x] Document the one-click flow and its limits.
- [x] Run backend suite, frontend build, and Playwright verification. Frontend build and Playwright passed; backend suite ran with 102 passed and 16 failures caused by the pre-existing missing `document_processing_jobs.stage` test schema column.
- [ ] Commit and push to the configured repository; confirm the hosted page exposes the new action.

