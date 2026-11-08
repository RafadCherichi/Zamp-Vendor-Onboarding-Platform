# Vendor onboarding: the decision behind the prototype

## Problem and target users

A vendor enters business and bank details, uploads proof, and waits for a buyer reviewer. The costly handoff is the comparison between the form and the proof: a disagreement can be missed, or an unclear request sends the vendor back without saying what to change. Procurement needs to know who owns the next step; the vendor needs a reason they can act on. This is the workflow described in the [case study guide](ASA%20Case%20Study%20%E2%80%94%20Candidate%20Guide.pdf) and product specification. Buyer volumes and turnaround times are **assumptions**, not measured facts.

## One-week product choice

The prototype prioritises a traceable, human approval decision over adding another simulated verification source. A field extracted from a bank proof must be compared with the number entered in the form, with a documented result and a blocking exception when they disagree. This choice was prompted by the [baseline grade](PROTOTYPE_GRADE.md): a fresh form ending 5679 and a cheque ending 5678 were approved because the extractor and validator used different field keys.

The [scenario dataset](testdata/vendor_scenario_dataset.xlsx) changes one variable at a time. The fresh mismatch now produces `B_BANK_ACCOUNT_NUM_MATCH:FAILED`, a vendor-owned correction and HTTP 400 on approval. A still-wrong correction remains blocked. A matching correction changes the check to `PASSED`; the reviewer must then resolve the exception before approving. An unreadable proof produces `UNVERIFIED` and asks for a clearer proof. The [run log](testdata/scenario_results.json) records these API observations. Simulated registry results are labelled as simulations; they are not proof of an official registration.

The expanded dataset also exposed a different approval gap: a GST certificate uploaded into the PAN proof slot could be approved. Submission now asks for a matching file, and the approval gate checks the latest required document versions as a second safeguard. The rule accepts an Udyam certificate as constitution proof for a sole proprietor, because that is an explicitly allowed option in this case's checklist. A [fresh browser run](testdata/fresh_browser_results.json) then completed form entry, uploads, submission and a reviewer decision, with the same reference visible after refresh and in the staff queue. That run exposed an older save response overwriting newer typing in the wizard; the newer local draft now remains in place until the full save before advancing.

## Measure the pilot

**Primary outcome:** median elapsed hours from a vendor's first submission to a recorded reviewer decision, for applications submitted during a defined four-week pilot. Report the number of decided cases and segment by constitution type. Publish the count and age of still-open applications beside the median so a faster median cannot hide a growing backlog.

**Safety guardrail:** known blocking cases incorrectly approved ÷ all labelled blocking cases tested. Report numerator, denominator, case IDs and document versions. The target for the labelled evaluation set is zero. A separate production audit should sample actual decisions, because synthetic cases cannot establish a real-world error rate.

**Secondary diagnostic:** median time from a correction request to a valid vendor response. Keep vendor wait time separate from active reviewer effort. Record timestamps for submission, each correction request, response and decision; review a sample to check the event log reflects what users saw. The pilot needs a baseline from the current email and spreadsheet process before claiming a time reduction. [Google's HEART framework](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/) supports linking a product goal to signals and measurable events.

## Buyer value hypothesis

All figures below are **planning assumptions**, not buyer measurements. The mechanism is limited to active reviewer follow-up time avoided by a clearer correction request; it does not turn vendor waiting days into staff hours or assumed hours into cash.

| Monthly cases | Cases needing correction | Reviewer minutes avoided per corrected case | Estimated reviewer capacity released in one month |
|---:|---:|---:|---:|
| 40 (low) | 15% | 6 | 0.6 hours |
| 80 (base) | 25% | 12 | 4.0 hours |
| 160 (high) | 35% | 20 | 18.7 hours |

Formula: `monthly applications × correction share × active minutes avoided ÷ 60`. The estimate is also the **one-month cost of waiting** if current rework continues unchanged: 0.6, 4.0 or 18.7 reviewer-hours, respectively. This excludes supplier delay, missed purchasing windows and other consequences because the case provides no evidence to price them.

**Recommended action:** run a four-week, limited pilot and measure actual active follow-up minutes, correction share, correction-cycle time and open-case age before expanding the workflow. Budget an assumed **one reviewer-hour per week (four hours total)** to capture comparable baseline and pilot cases. That is the direct cost of acting in this model; it is not an engineering-cost estimate. In the low case, the modeled monthly capacity gain (0.6 hours) does not repay that measurement effort within the pilot month. In the base case it matches the assumed effort, and in the high case it exceeds it. Do not claim value from this prototype alone.

The recommendation changes if the measured correction rate or time saved falls enough that expected capacity released is consistently below the effort to operate and measure the process, if open-case age grows, or if correct submissions are frequently held. Keep the existing safety guardrail at zero known blocking cases incorrectly approved, and add a counter-metric for correct cases incorrectly blocked. A pilot should time active follow-up for comparable cases and report both outcomes; no saving is claimed from the synthetic prototype run.

## Interface direction

The visual system uses warm paper, dark ink and one green action colour. Status and the next task appear before decorative metrics. The reviewer desk is a compact case queue; the vendor sees a plain-language request or recorded decision. This follows the [GOV.UK error guidance](https://design-system.service.gov.uk/components/error-message/) on specific, actionable errors and the [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) requirements for text contrast, visible focus and meaning beyond colour. A fresh build was checked at 1440px for the reviewer and 390px for the vendor. The [browser observations](testdata/ui_results.json) and [screenshots](grade_evidence/iteration2-vendor-action.png) show the correction request and terminal reason without horizontal overflow. Independent task comprehension and a complete keyboard journey remain to be observed with a first-time participant.
