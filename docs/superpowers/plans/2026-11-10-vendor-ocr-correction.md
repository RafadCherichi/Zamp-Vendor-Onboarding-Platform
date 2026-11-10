# Vendor OCR Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow only the applicant/vendor to correct OCR-extracted document fields with an explanation while preserving the original extraction and requiring normal reviewer approval.

**Architecture:** Adapt the existing uncommitted reviewer-only correction work into a vendor-owned correction flow. Keep extracted values immutable; store corrected value, note, actor, timestamp, and document-version association; use the correction for subsequent validation and show provenance in both vendor and reviewer views.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TypeScript, pytest, Vite.

**Spec:** `docs/superpowers/specs/2026-11-10-vendor-ocr-correction-design.md`

## Global Constraints

- Vendor correction authorization must be `RoleEnum.VENDOR` and scoped to that vendor's own application.
- Original OCR values and evidence must remain unchanged.
- Corrections require a non-empty value and a short reason, are tied to the current document version, and are audited.
- Revalidation must use the corrected value; correction must not approve or resolve an exception by itself.
- Preserve existing unrelated working-tree changes and extend the existing OCR correction changes in place.

## Review Focus

- Reviewer/admin token tries to edit OCR: must be denied.
- Vendor targets another vendor's application: must receive the scoped not-found/denial response.
- Vendor submits a stale field ID after replacing a document: must be rejected without changing either version.
- Vendor submits blank/whitespace correction or reason: must be rejected.
- Revalidation fails after saving: correction remains audited and the UI clearly says checks still need to be rerun.

---

### Task 1: Vendor-only API and persistence

**Files:**
- Modify: `backend/app/models/extraction.py`
- Modify: `backend/app/schemas/extraction.py`
- Modify: `backend/app/api/endpoints/applications.py`
- Modify: `backend/app/services/validation/layer_b_consistency.py`
- Modify: `backend/alembic/versions/9c3a72ef1b04_add_human_reviewed_ocr_values.py` (adapt existing uncommitted migration)
- Test: `backend/tests/test_document_processing.py`

**Interfaces:**
- Use a vendor-specific extraction-field correction route, available only to the applicant who owns the unsubmitted application.
- The request carries corrected value and reason; response returns original OCR and vendor correction provenance.

- [x] **Step 1: Write failing API tests** for vendor-owned correction persistence, original OCR preservation, audit event, unauthorized reviewer/admin roles, cross-vendor scope, stale version, and blank reason/value.
- [x] **Step 2: Run those tests and confirm expected failures** against the current reviewer-only endpoint.
- [x] **Step 3: Adapt model, migration, schema, and endpoint** to store vendor correction separately and authorize only the owning vendor for the current document version.
- [x] **Step 4: Change validation precedence** to use corrected value, then normalized OCR, then original OCR, preserving the original extraction fields.
- [x] **Step 5: Run the targeted API tests** and confirm all authorization, validation, and persistence cases pass.

### Task 2: Applicant correction interface

**Files:**
- Modify: `frontend/src/components/vendor/StepDocumentChecklist.tsx`
- Modify: `frontend/src/api/applications.ts`
- Modify: `frontend/src/types/application.ts`
- Test: backend API contract tests from Task 1; use existing browser tooling for an end-to-end smoke journey if available without adding dependencies.

**Interfaces:**
- Vendor component consumes detailed extraction data and submits `{ corrected_value, reason }` for one field and current document version.
- API response distinguishes original OCR reading from the applicant's corrected value and reports revalidation state.

- [ ] **Step 1: Add failing coverage or a focused component-level reproduction** showing OCR fields are read-only today and the applicant needs an editable correction path; avoid adding a test framework dependency solely for this feature.
- [x] **Step 2: Implement the correction form** in the vendor’s OCR evidence panel with confidence, original OCR value, editable vendor value, required reason, and a clear save/recheck action.
- [x] **Step 3: Show saved correction provenance and revalidation outcome**; if validation cannot rerun, state that the correction saved but checks remain incomplete.
- [x] **Step 4: Run `npm run build`** and verify the UI compiles.

### Task 3: Reviewer evidence and guardrail verification

**Files:**
- Modify: `frontend/src/components/review/ApplicationDetailsWorkspace.tsx`
- Modify: `backend/app/api/endpoints/applications.py` and response schemas as needed
- Test: `backend/tests/test_document_processing.py`

- [x] **Step 1: Add failing API assertion** that reviewer detail shows original OCR and vendor correction provenance while reviewer/admin cannot mutate it.
- [x] **Step 2: Remove reviewer/admin mutation controls** from the existing uncommitted reviewer workspace; retain read-only original-vs-corrected evidence for review.
- [x] **Step 3: Run the API tests and `npm run build`.**
- [ ] **Step 4: Record a fresh browser walkthrough** of vendor preview → OCR extraction → vendor correction/reason → revalidation → reviewer comparison, with no applicant data changed outside the disposable recording environment.

## Completion Evidence

- Targeted backend tests pass for ownership, versioning, preservation, audit, and correction precedence.
- Frontend production build passes.
- Fresh browser evidence shows the vendor made the correction and the reviewer sees both the OCR reading and corrected value.
- The final video script states the product problem, OCR role, human correction, validation guardrails, human approval, and synthetic-data limitation accurately.
