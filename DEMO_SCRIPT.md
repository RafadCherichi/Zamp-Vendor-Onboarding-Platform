# Zamp PS-2: five-minute demonstration

**Audience:** procurement lead, risk reviewer and case-study evaluator

**Format:** live local prototype or one continuous screen recording
**Evidence:** [scenario workbook](testdata/vendor_scenario_dataset.xlsx), [fresh browser run](testdata/fresh_browser_results.json), [decision note](CASE_STUDY_DECISION_NOTE.md)

Prepare a seeded demo in a disposable database before recording. Keep two browser sessions ready: reviewer (`reviewer@apex.com`) and vendor with a correction (`vendor.mismatch@sharmaworks.in`). Use the prepared clean case `APP-2026-CLEAN-001` for the decision. The separate fresh-browser run shows that a new vendor can enter all seven steps, upload proofs, submit, refresh and receive the outcome; do not claim the prepared case itself is new.

| Time | Screen and live action | Say |
|---|---|
| **0:00–0:35** | Reviewer queue. Point to case status, issues and owner. | “The buyer's handoff is simple to describe and easy to get wrong: a vendor enters details, sends proofs, and a reviewer compares them before approving payment setup. A vague correction request sends work back and forth. This prototype puts the evidence, next owner and decision in one process.” |
| **0:35–1:30** | Open the clean Tata case; show the submitted account and proof, validation result and source labels. Approve it with a short reason. Refresh the queue to show the saved decision. | “A complete case reaches human review. The system extracts and compares details, but a person records the approval. The account comparison, document version and reason remain available after refresh. Registry responses in this demo are simulated, and the interface labels them as such.” |
| **1:30–2:55** | Open the Sharma mismatch. Show the entered account and cheque value, then try approval so the block is visible. Switch to vendor session and point to the specific correction field and document upload. Send a correction if rehearsed in this disposable run. | “This is a material disagreement, so approval is blocked. The vendor sees what differs and where to fix it. Our labelled test also tries a still-wrong correction: that remains blocked. A matching correction reruns the check; the reviewer resolves the exception before approving. The correction history is preserved.” |
| **2:55–3:35** | Open the registry-unavailable case or the labelled V11 result. Show owner and status. | “An unavailable registry is unknown evidence, not proof that the vendor is wrong. The case stays with procurement for retry or escalation. We do not ask the vendor to upload the same document again, and the approval gate stays closed.” |
| **3:35–4:20** | Show the scenario workbook and the four vendor types. Point to the wrong-slot and missing-Udyam rows. | “Fourteen synthetic cases cover company, proprietor, partnership and LLP rules. They include unreadable proof, tax identity conflict, a wrong document slot and a missing MSME certificate. All 14 matched their prewritten expectations in this run. Checklist-only cases are marked as such; this does not measure real-world accuracy.” |
| **4:20–5:00** | Show the decision note's KPI and value estimate. End on reviewer queue. | “For a pilot, I would measure median hours from first submission to recorded decision, beside the count and age of open cases. The safety guardrail is falsely approved known blockers. At an assumed 80 cases a month, a 25% correction rate and 12 minutes saved per correction, the hypothesis is four reviewer-hours a month. We need a buyer baseline and live pilot before claiming savings.” |

## Presenter checks

- Rehearse with a timer; trim screen navigation before claiming this fits five minutes. One run or recording must show a happy decision and an edge case executing.
- Do not call a format check or simulated provider result an authoritative registry verification. Do not claim a 21-day baseline, a 48-hour turnaround, a 75% improvement, zero human error or fraud prevention from these synthetic tests.
- If asked about the product choice, explain that the bank account comparison and correction path took priority over adding another simulated data source. A fresh conflict was incorrectly approved in the baseline and now blocks until the evidence agrees.
- If asked about limits, state that first-time vendor comprehension, full keyboard use, measured buyer savings and official registry integration still need evidence.
