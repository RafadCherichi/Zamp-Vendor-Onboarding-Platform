# Zamp PS-2: five-minute demo script

**Audience:** procurement lead, risk reviewer and case-study evaluator
**Target length:** 4:40, leaving 20 seconds for screen transitions
**Status:** script prepared; timed narration and recording still required
**Evidence:** [scenario workbook](testdata/vendor_scenario_dataset.xlsx), [current scenario results](testdata/scenario_results.json), [fresh browser results](testdata/fresh_browser_results.json), [decision note](CASE_STUDY_DECISION_NOTE.md)

## Before starting

- Reset the demo to a disposable database and use synthetic data only.
- Keep reviewer and vendor sessions open in separate windows.
- Seed the clean case `APP-2026-CLEAN-001` and bank-conflict case `APP-2026-MISM-002`; don't describe either seeded case as a new submission.
- Have the exact-run view ready. Keep a fresh invite-to-submit browser run available if asked how a new case enters the process.
- Start a timer. Do not pause to browse source code or the full workbook during the main story.

| Time | Show and do | Narration |
|---|---|---|
| **0:00–0:30** | Start at the procurement queue. Point out status, next owner and action. | “A vendor enters business details and proof; procurement needs to decide whether the case is ready, needs more information, or cannot proceed. The costly handoff is comparing the form with the proof and telling the vendor exactly what to do next.” |
| **0:30–1:25** | Open the clean case. Show form evidence against extracted proof, source/simulation labels and findings. Approve with a reason; refresh and show the saved result. | “The system compares submitted details with the evidence and applies the checklist. It can make the case ready for human review; a reviewer records the approval. The decision and its evidence remain inspectable. Registry responses here are simulated, not live government verification.” |
| **1:25–2:35** | Open the bank-conflict case. Show the mismatch and blocked approval. Switch to the vendor view and show the correction request. If rehearsed, submit one still-wrong correction and show that it remains blocked. | “These account details disagree, so the approval is blocked. The vendor gets a specific request and a clear next step. We also test a still-wrong correction: the check remains failed. A matching correction passes the comparison, but the reviewer still resolves the exception before approval.” |
| **2:35–3:15** | Open Processing Runs. Select one exact run and show findings, counts, reason and separate Open case action. | “The dashboard keeps the run and its output together. I can open the saved findings and then move to the current case. The upload pipeline shows actual document-reading stages; business validation is visible here as saved findings, not as a live animated sequence.” |
| **3:15–3:55** | Point to the unreadable-proof and unavailable-provider scenario outputs in the prepared result summary; show their owner/action. | “Unreadable proof is uncertainty and asks for clearer evidence. An unavailable check is not evidence against the vendor; it stays with procurement for retry or review. These outcomes are separate from a confirmed mismatch.” |
| **3:55–4:25** | Show the dataset summary: 14 case IDs across company, proprietor, partnership and LLP; 15 result records because one case has correction steps. | “The prepared synthetic set varies the vendor type and evidence, including conditional documents and wrong or unreadable proof. All 15 recorded assertions passed in this run. That validates these fixtures; it does not estimate real-world accuracy.” |
| **4:25–4:40** | End on the queue or decision note's metric. | “For a pilot, I would track median hours from first submission to recorded decision, alongside open-case count and age. The guardrail is zero known blockers incorrectly approved; we would also watch valid cases incorrectly held. We need a buyer baseline before claiming time saved.” |

## Rehearsal and evidence checklist

- Record one continuous narrated screen capture and time it. If it exceeds five minutes, shorten transitions and remove detail; do not speed-read.
- Ask a first-time viewer what the vendor supplied, what the product decided, who acts next and why the buyer should care. Record their unaided answer before explaining.
- Verify the evaluator-facing URL in a clean browser and confirm that the demo data is present or that reset/setup instructions work.
- Keep synthetic documents and identifiers in the public demo. Do not claim a simulated provider is an official integration.
- Do not claim turnaround improvements, fraud prevention, zero human error or reviewer-time savings as measured results. Any value estimate is an explicitly labelled planning assumption in [the decision note](CASE_STUDY_DECISION_NOTE.md).
