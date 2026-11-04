# Vendor Onboarding Platform — 5-Minute Executive Demo Script

> **Target Audience:** Enterprise Business Evaluator, Head of Procurement, Chief Risk Officer  
> **Platform Version:** 1.0.0 (India Enterprise Compliance Edition)  
> **Total Duration:** Exactly 5 minutes (300 seconds)  
> **Theme:** How deterministic automation, explainable AI extraction, and human-in-the-loop workflows compress India enterprise vendor onboarding from 21 days to under 48 hours without compromising statutory compliance.

---

## Chronological Demo Timeline

| Timestamp | Phase | Focus | Primary Screen |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:30** | The Problem | The Compliance Bottleneck in India B2B | Procurement Dashboard |
| **0:30 – 1:15** | Vendor Experience | Invitation-First & Conditional Checklist | Vendor Onboarding Wizard |
| **1:15 – 2:00** | Processing & Validation | Explainable OCR & 4-Layer Validation | Document Processing & Validation Findings |
| **2:00 – 3:15** | Exception Resolution | Clarification, Correction & Selective Revalidation | Vendor Exceptions Banner & Inline Correction |
| **3:15 – 4:30** | Decision Workspace | 7-Section Reviewer Workspace & Approval Gate | Reviewer Decision Center |
| **4:30 – 5:00** | Business Value | Audit Integrity, Scalability & Metrics | Procurement Analytics & Audit Trail |

---

## Detailed Minute-by-Minute Script & Presenter Cues

### Minute 0:00 – 0:30 | Problem Setup: The Compliance Friction
**Screen:** Procurement Officer Dashboard (`http://localhost:5173/procurement`)  
**Login:** `procurement@apex.com` / `Password123!`

- **Spoken Narrative:**  
  *"Enterprise vendor onboarding in India is notoriously slow and high-risk. Between GSTIN format errors, name mismatches between PAN cards and bank accounts, unverifiable MSME claims, and fragmented email clarifications, the average enterprise takes 21 days to onboard a new supplier. High-volume teams drown in manual PDF audits and face statutory penalties when bad data slips through."*
- **Visual Action:**  
  Point to the top KPI metrics on the dashboard:
  - Total Active Applications
  - Open Exceptions (categorized by High, Critical, and Medium)
  - Processing Bottlenecks
- **Key Takeaway Highlighted:**  
  *"Our platform replaces email tennis and static forms with an intelligent, invitation-governed system that automates document extraction, verifies against Indian statutory rules, and guarantees total auditability."*

---

### Minute 0:30 – 1:15 | Vendor Experience: Invitation-First & Smart Checklist
**Screen:** Vendor Registration & Onboarding Wizard (`http://localhost:5173/invite/...` or Vendor Login)  
**Login:** `vendor.mismatch@sharmaworks.in` / `Password123!`

- **Spoken Narrative:**  
  *"Public self-registration creates spam and vendor data contamination. In this platform, onboarding is strictly invitation-first. When a buyer invites a supplier, a secure tokenized link is generated.  
  As the vendor fills out their business identity, our dynamic checklist engine evaluates statutory requirements in real-time. A sole proprietorship requires an individual PAN and establishment certificate. Switch to a Private Limited entity or LLP, and the checklist dynamically demands a Certificate of Incorporation, CIN, and Board Resolution for authorized signatories. GST certificate requirements toggle based on whether the supplier claims GST registration."*
- **Visual Action:**  
  - Show the 5-step stepper: Identity, Tax/Registration, Contact, Banking, Declarations.
  - Show document upload slots adapting dynamically to the selected constitution.
- **Key Takeaway Highlighted:**  
  *"Vendors never wonder which documents to provide—the compliance rules are baked into the checklist."*

---

### Minute 1:15 – 2:00 | Document Processing: Explainable OCR & Multi-Layer Validation
**Screen:** Reviewer Workspace — Case 1 (`APP-2026-CLEAN-001`, Tata Industrial Supplies)  
**Login:** `reviewer@apex.com` / `Password123!`

- **Spoken Narrative:**  
  *"When documents are uploaded, our multi-modal extraction pipeline analyzes both selectable text and scanned image files. Crucially, the platform never hallucinates or blindly trusts AI. Every extracted field—PAN, GSTIN, Bank IFSC, Beneficiary Name—is paired with an extraction confidence score and visual bounding coordinates. If an unreadable image is uploaded, it is flagged as LOW CONFIDENCE rather than inventing data."*
- **Visual Action:**  
  - Navigate to `APP-2026-CLEAN-001` in the Reviewer Workspace.
  - Open the **Validation Engine** tab.
  - Show the 4 deterministic layers:
    - **Layer A (Input Syntax):** Mod-36 GSTIN check digit algorithm, PAN 4th character constitution check (`C` for Company, `P` for Proprietorship), IFSC statutory format.
    - **Layer B (Cross-Field Consistency):** Embedded PAN in GSTIN matching declared PAN, PAN name matching GST legal name using entity-aware token matching.
    - **Layer C (External Verifications):** Simulated sandbox checks against Income Tax PAN, GSTN, and Bank Account penny-drop.
    - **Layer D (Duplicate Detection):** Cross-application similarity scan preventing duplicate supplier creation.
- **Key Takeaway Highlighted:**  
  *"Clean applications pass all 4 layers with zero human effort, enabling same-day straight-through processing."*

---

### Minute 2:00 – 3:15 | Exception Management: Clarification & Vendor Correction
**Screen:** Case 2 (`APP-2026-MISM-002`, Sharma Engineering Works)  
**Switching between:** Reviewer View and Vendor View

- **Spoken Narrative:**  
  *"Now let's examine what happens when something is wrong. In Case 2, the vendor entered bank account number `9876543210123`, but their cancelled cheque and penny-drop showed a discrepancy.  
  Rather than rejecting the supplier, our system raised an actionable exception: `BANK_DETAIL_MISMATCH` with HIGH severity."*
- **Visual Action (Reviewer):**  
  - Show that the Reviewer's **Approve** button is disabled with a red policy banner: *"Approval Blocked: Unresolved HIGH exception."*
  - Click **Request Clarification**, type instructions: *"Please update registered account number to match cheque."*
  - Observe application transition immediately from `UNDER_REVIEW` to `ACTION_REQUIRED`.
- **Visual Action (Vendor):**  
  - Switch to Vendor session (`vendor.mismatch@sharmaworks.in`).
  - Notice the amber **Vendor Clarification Banner** prominently displayed at the top with reviewer instructions.
  - Click **Correct Field**, update account number to `502000998877`, enter explanation, and click **Submit Correction**.
- **Visual Action (Under the Hood):**  
  - Show that a `FieldCorrectionRecord` is created preserving the audit trail of what changed.
  - Show that application transitions back to `UNDER_REVIEW`—it is **never** automatically approved.
- **Key Takeaway Highlighted:**  
  *"Exceptions are resolved in minutes without phone calls or lost emails, with complete version preservation."*

---

### Minute 3:15 – 4:30 | Reviewer Decision Workspace: Policy Gates & Human Sign-Off
**Screen:** Reviewer Decision Workspace (`http://localhost:5173/reviewer`)  
**Login:** `reviewer@apex.com` / `Password123!`

- **Spoken Narrative:**  
  *"The reviewer returns to their unified 7-section workspace. Everything needed for an audit-grade decision is visible in one panel:
  1. Header Overview & Assignment
  2. Business Identity & Masked Statutory Data (PAN and Bank accounts safely masked)
  3. Versioned Document Artifacts
  4. 4-Layer Validation Findings
  5. Exception Resolution History & Correction Proof
  6. Authoritative External Verification Logs
  7. Chronological Audit Trail."*
- **Visual Action:**  
  - Resolve the corrected exception with sign-off notes: *"Account verified against corrected cheque."*
  - Point out that the **Approve Application** button turns green as the statutory policy gate passes.
  - Click **Approve Application**, enter decision notes: *"Statutory documents verified. Approved for vendor master creation."*
  - Confirm instant transition to `APPROVED`, showing the verified checkmark badge.
- **Key Takeaway Highlighted:**  
  *"Enterprise risk is protected by deterministic policy gates. Reviewers cannot accidentally sign off on an incomplete file."*

---

### Minute 4:30 – 5:00 | Business Value: Audit Integrity & Demo Reset
**Screen:** Admin Dashboard & Demo Reset Engine (`http://localhost:5173/admin`)  
**Login:** `admin@apex.com` / `Password123!`

- **Spoken Narrative:**  
  *"To summarize the business value:
  - **75% reduction in onboarding cycle time** (from 21 days to under 48 hours).
  - **Zero human error in statutory validation** via automated Mod-36 GSTIN checks and constitution-aware PAN rules.
  - **Bank fraud prevention** via automated penny-drop matching.
  - **100% immutable audit log** recording every upload, edit, validation run, and approval.
  And for continuous testing and demonstrations, any administrator can click 'Reset & Re-Seed Demo' to instantly restore all 3 canonical scenarios to a pristine state in seconds."*
- **Visual Action:**  
  - Click **Reset & Re-Seed Demo** on the Admin Dashboard.
  - Watch the live toast confirmation and instant queue refresh.
- **Closing Statement:**  
  *"This is modern, automated, and explainable vendor onboarding built specifically for Indian enterprise statutory compliance."*
