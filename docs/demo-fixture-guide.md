# Fictional demonstration fixtures

All identifiers and documents below are synthetic and must not be used for official verification.

| Case | Expected behaviour |
| --- | --- |
| Apex Components practice account | Company-matched autofill and public proof files submit with clear checks. PAN ABCPV1234F; bank 8876543210123; Udyam UDYAM-MH-02-0054321. Vendor declarations remain manual in the UI. |
| Tata clean case | Assigned reviewer can approve; vendor receives an in-app notice and decision receipt. |
| Sharma correction case | Entered bank 9876543210123 differs from proof 60200012345678. Correct the value to the proof, then reviewer resolves the request and decides. |
| Apex Logistics warning case | Required evidence is present. Simulated MCA fixture AAA-1234 times out. A separately labelled seeded duplicate concern requires review. |

Unknown identifiers remain unverified. Registered names come from independent fixtures, never from the submitted company name. The product uses in-app notifications; email delivery and downstream purchasing/payment activation are not implemented.

Regression: backend/tests/test_demo_correction_journey.py creates a disposable database and validates the shipped autofill/proofs plus a two-request correction, reviewer reassessment and vendor approval notice. It never resets hosted data.
