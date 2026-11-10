# Vendor OCR Correction Design

## Intent

Let the vendor/applicant correct OCR-extracted document fields when the extraction does not match the source document. This makes the person who supplied the evidence responsible for confirming its contents, while keeping OCR assistance transparent and preserving human oversight.

## Approved approach

Store a vendor correction separately from the original OCR value. In the vendor document checklist, show the source document beside extracted values and confidence; let the applicant edit a value and provide a short reason. Record the actor, timestamp, document version, original value, corrected value, and reason. Re-run affected validation after saving, and show both readings to the reviewer. The correction itself does not establish official verification or approve the application.

## Approaches considered

- **Vendor correction overlay (chosen):** preserve OCR output and store a vendor-authored value and reason separately. Supports transparent correction and reliable audit history.
- **Replace and reprocess only:** keeps provenance but forces a new upload even when the document is clear and OCR alone was wrong.
- **Overwrite OCR output:** simpler display model, but loses what the extraction actually returned and weakens review/audit evidence.

## Goals

- Only the applicant who owns the application can save a correction.
- The correction applies to the current document version and cannot alter another vendor's evidence.
- Preserve and display original OCR, corrected value, reason, actor, and timestamp.
- Use a saved correction for subsequent consistency checks and rerun validation after changes.
- Keep final approval with the assigned human reviewer.

## Non-goals

- Let vendors rewrite uploaded files in place.
- Let vendors change OCR classification, confidence, evidence snippets, or page coordinates.
- Treat a vendor correction as independent registry verification or as a reviewer decision.
- Change reviewer exception-resolution or approval permissions beyond removing reviewer/admin ownership of OCR correction.

## Constraints and implementation notes

- The worktree already contained uncommitted reviewer-only OCR correction work. Adapt it to applicant ownership while preserving its validation and evidence goals.
- Alembic previously had two heads. Merge the vendor correction and processing-stage revisions so production can run `alembic upgrade head` reliably.
- Current document-version checks must reject edits to stale field IDs or old document versions.
- Persist sensitive identifiers using existing masking behavior in audit details and user-facing summaries where applicable.
- Maintain existing tenant scoping and API response conventions.

## Success criteria

- A vendor can inspect, correct, explain, save, and recheck an extracted field on their own application.
- Reviewer and admin tokens cannot call the vendor correction endpoint.
- A vendor cannot edit another applicant's case or stale document version.
- Original OCR remains unchanged and available beside the vendor correction.
- Validation uses the corrected value, audit history records the change, and the case still requires the ordinary reviewer decision.
