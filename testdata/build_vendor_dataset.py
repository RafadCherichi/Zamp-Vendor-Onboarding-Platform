"""Build the editable Excel scenario log from the synthetic case manifest."""

import json
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HERE = Path(__file__).resolve().parent
source = json.loads((HERE / "vendor_scenarios.json").read_text(encoding="utf-8"))
results_file = HERE / "scenario_results.json"
results = {row["id"]: row for row in json.loads(results_file.read_text(encoding="utf-8"))["cases"]} if results_file.exists() else {}
ui_file = HERE / "ui_results.json"
ui_results = json.loads(ui_file.read_text(encoding="utf-8")) if ui_file.exists() else {}
output = HERE / "vendor_scenario_dataset.xlsx"
wb = Workbook()
wb.calculation.fullCalcOnLoad = True
overview = wb.active
overview.title = "Overview"
cases = wb.create_sheet("Cases")
ink, green, paper, line = "20332D", "255644", "F7F5EF", "D7D9D0"

overview.sheet_view.showGridLines = False
overview.merge_cells("A1:H2")
overview["A1"] = "Vendor onboarding / scenario dataset"
overview["A1"].font = Font(name="Aptos Display", size=20, bold=True, color="FFFFFF")
overview["A1"].fill = PatternFill("solid", fgColor=ink)
for row in overview["A1:H2"]:
    for cell in row:
        cell.fill = PatternFill("solid", fgColor=ink)

last = len(source["cases"]) + 3
for r, pair in enumerate([
    ("Cases in dataset", len(source["cases"])),
    ("Passed", f'=COUNTIF(Cases!P4:P{last},"PASS")'),
    ("Needs review", f'=COUNTIF(Cases!P4:P{last},"REVIEW")'),
    ("Not run", f'=COUNTIF(Cases!P4:P{last},"NOT RUN")'),
    ("Core cases", sum(c["priority"] == "Core" for c in source["cases"])),
    ("Dataset date", source["version"]),
], start=4):
    overview.cell(r, 1, pair[0])
    overview.cell(r, 2, pair[1])
    overview.cell(r, 1).font = Font(name="Aptos", size=11, bold=True, color=ink)

overview.merge_cells("A11:H11")
overview["A11"] = "How to run the cases"
overview["A11"].fill = PatternFill("solid", fgColor=green)
overview["A11"].font = Font(name="Aptos", size=12, bold=True, color="FFFFFF")
instructions = [
    "1. Use a disposable buyer organisation, database and upload directory for each case.",
    "2. Generate or upload synthetic documents matching the evidence columns. Never use real vendor data.",
    "3. Record the actual finding and decision in columns N and O on the Cases tab.",
    "4. Result compares the observed finding and decision with the prewritten expectation.",
    "5. Record an API response, screenshot or run log reference in column Q. Review wording separately.",
    "6. A simulated provider result is not an authoritative registry verification.",
]
for r, instruction in enumerate(instructions, start=12):
    overview.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    overview.cell(r, 1, instruction)
overview.merge_cells("A19:H19")
overview["A19"] = source["notice"]
overview["A19"].font = Font(name="Aptos", size=10, italic=True, color="5E6A62")
overview.column_dimensions["A"].width = 32
overview.column_dimensions["B"].width = 18
for col in "CDEFGH":
    overview.column_dimensions[col].width = 12
for r in range(11, 20):
    overview.row_dimensions[r].height = 27

cases.sheet_view.showGridLines = False
cases.freeze_panes = "A4"
cases.merge_cells("A1:Q1")
cases["A1"] = "Synthetic vendor cases / expected vs observed"
cases["A1"].font = Font(name="Aptos Display", size=18, bold=True, color="FFFFFF")
cases["A1"].fill = PatternFill("solid", fgColor=ink)
for cell in cases[1]:
    cell.fill = PatternFill("solid", fgColor=ink)
cases.merge_cells("A2:Q2")
cases["A2"] = "Change only the intended variable in each case. Blank observed cells mean the case has not been run."
cases["A2"].font = Font(name="Aptos", size=10, color="657168")
headers = ["Case ID", "Priority", "Vendor type", "Legal name", "Constitution", "PAN (synthetic)", "GST", "Bank entered", "Bank proof", "Injected fault", "Expected check", "Expected decision", "Next owner", "Observed check", "Observed decision", "Result", "Evidence / notes"]
for c, label in enumerate(headers, start=1):
    cell = cases.cell(3, c, label)
    cell.fill = PatternFill("solid", fgColor=green)
    cell.font = Font(name="Aptos", size=10, bold=True, color="FFFFFF")
    cell.alignment = Alignment(vertical="center", wrap_text=True)
cases.row_dimensions[3].height = 32

for r, case in enumerate(source["cases"], start=4):
    values = [case[key] for key in ("id", "priority", "segment", "legal_name", "constitution", "pan", "gst", "bank_entered", "bank_proof", "fault", "expected_check", "expected_decision", "owner")]
    for c, value in enumerate(values, start=1):
        cases.cell(r, c, value)
    observed = results.get(case["id"])
    if observed:
        if case["id"] == "V14":
            if ui_results.get("rejection_reason_visible") and ui_results.get("rejected_correction_banner_hidden"):
                cases.cell(r, 14, "VENDOR_REJECTION_REASON:VISIBLE")
                cases.cell(r, 15, case["expected_decision"])
                cases.cell(r, 17, "API and 390px browser checked; see ui_results.json and iteration2-vendor-rejected.png")
            else:
                cases.cell(r, 14, "VENDOR_REJECTION_REASON:VISIBLE (API)")
                cases.cell(r, 15, "Reason present in API; browser view not verified")
                cases.cell(r, 17, "API rejection and vendor payload checked. Terminal UI still needs a browser check.")
        else:
            cases.cell(r, 14, observed["observed_check"])
            cases.cell(r, 15, observed["observed_decision"])
            evidence = f"API {observed['approval_http']}; vendor {observed['vendor_status']}; {observed['vendor_action_count']} vendor actions; see scenario_results.json"
            if case["id"] == "V03" and results.get("V03-CORRECTION", {}).get("pass"):
                evidence += "; wrong correction blocked; matching correction approved after review"
            if case["id"] == "V12":
                evidence += f"; replaced wrong-slot file, approval HTTP {observed['recovery_approval_http']}"
            cases.cell(r, 17, evidence)
    cases.cell(r, 16, f'=IF(OR(N{r}="",O{r}=""),"NOT RUN",IF(AND(N{r}=K{r},O{r}=L{r}),"PASS","REVIEW"))')
    cases.row_dimensions[r].height = 58
    for c in range(1, 18):
        cell = cases.cell(r, c)
        cell.fill = PatternFill("solid", fgColor="FFF6DD" if c in (14, 15) else "E8F1EB" if c == 16 else paper)
        cell.font = Font(name="Aptos", size=10, color=ink)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = Border(bottom=Side(style="thin", color=line))

widths = [11, 12, 21, 31, 18, 18, 16, 18, 18, 36, 35, 42, 17, 35, 42, 13, 38]
for c, width in enumerate(widths, start=1):
    cases.column_dimensions[get_column_letter(c)].width = width
cases.auto_filter.ref = f"A3:Q{last}"
wb.save(output)
check = load_workbook(output, read_only=True)
assert check["Cases"].max_row == last
assert check["Cases"]["K4"].value == "B_BANK_ACCOUNT_NUM_MATCH:PASSED"
print(f"Saved {len(source['cases'])} synthetic cases: {output}")
