import os
import sys
import time
from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Users\91994\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe"
BASE_URL = "http://127.0.0.1:5173"
SCREENSHOT_DIR = "audit_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def login(page, email, password="Password123!"):
    page.goto(f"{BASE_URL}/")
    page.wait_for_selector("input[type='email']", timeout=10000)
    page.fill("input[type='email']", email)
    page.fill("input[type='password']", password)
    page.click("button[type='submit']")
    time.sleep(1)

def sign_out(page):
    btn = page.query_selector("button:has-text('Sign Out')")
    if btn:
        btn.click()
        page.wait_for_selector("input[type='email']", timeout=10000)
        time.sleep(0.5)

def run_audit():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--proxy-server=direct://", "--disable-gpu", "--no-sandbox"]
        )

        # -------------------------------------------------------------
        # DESKTOP AUDIT (1440x900)
        # -------------------------------------------------------------
        print("\n=== Running Desktop Audit (1440x900) ===")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login Screen
        print("[Desktop] Login screen...")
        page.goto(f"{BASE_URL}/")
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_01_login.png"))

        # 2. Procurement Dashboard
        print("[Desktop] Procurement dashboard...")
        login(page, "procurement@apex.com")
        page.wait_for_selector("text=Procurement & Onboarding Operations", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_02_procurement_dash.png"))

        # Diagnostics panel
        diag_btn = page.locator("button:has-text('Foundation Environment Diagnostics')")
        if diag_btn.count() > 0:
            diag_btn.click()
            time.sleep(0.5)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_02b_procurement_diagnostics.png"))
            diag_btn.click()
            time.sleep(0.3)

        # Dispatch Invitation Modal
        page.click("button:has-text('Dispatch Invitation')")
        page.wait_for_selector("text=Dispatch Vendor Onboarding Invitation", timeout=5000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_03_dispatch_modal.png"))
        page.click("button:has-text('Cancel')")
        time.sleep(0.3)

        # Invitations Register
        page.click("button:has-text('Invitation Register')")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_04_invitation_register.png"))
        sign_out(page)

        # 3. Reviewer Queue & Cases
        print("[Desktop] Reviewer workspace...")
        login(page, "reviewer@apex.com")
        page.wait_for_selector("text=Reviewer & Approver Workspace", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_05_reviewer_queue.png"))

        # Case 1: Clean Approval (Tata)
        print("[Desktop] Case 1 Overview & Tabs...")
        page.locator("tr:has-text('APP-2026-CLEAN-001')").locator("button:has-text('Inspect')").click()
        page.wait_for_selector("text=APP-2026-CLEAN-001", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_06_case1_overview.png"))

        # Case 1 Tabs
        for tab_label, code in [
            ("B. Company Details", "tab_b_company"),
            ("C. Documents", "tab_c_docs"),
            ("D. 4-Layer Validation", "tab_d_validation"),
            ("F. Registries", "tab_f_registries"),
            ("G. Activity Trail", "tab_g_audit")
        ]:
            tab_btn = page.locator(f"button:has-text('{tab_label}')")
            if tab_btn.count() > 0:
                tab_btn.click()
                time.sleep(0.4)
                page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"desktop_07_case1_{code}.png"))

        # Approval Modal
        page.locator("button:has-text('A. Overview & Gates')").click()
        time.sleep(0.3)
        page.click("button:has-text('Approve Vendor')")
        page.wait_for_selector("text=Approve Vendor Application", timeout=5000)
        time.sleep(0.4)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_08_case1_approval_modal.png"))
        page.click("button:has-text('Cancel')")
        time.sleep(0.3)

        # Case 2: Mismatch (Sharma)
        print("[Desktop] Case 2 Exceptions & Clarification...")
        page.locator("button[title*='Back to Application Queue']").click()
        page.wait_for_selector("text=Reviewer & Approver Workspace", timeout=10000)
        time.sleep(0.5)
        page.locator("tr:has-text('APP-2026-MISM-002')").locator("button:has-text('Inspect')").click()
        page.wait_for_selector("text=APP-2026-MISM-002", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_09_case2_overview_blocked.png"))

        page.click("button:has-text('E. Exceptions')")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_10_case2_exception_tab.png"))

        page.click("button:has-text('Request Clarification')")
        page.wait_for_selector("text=Request Clarification from Vendor", timeout=5000)
        time.sleep(0.4)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_11_case2_clarification_modal.png"))
        page.click("button:has-text('Cancel')")
        time.sleep(0.3)

        # Case 3: Unavailable Registry (Apex)
        print("[Desktop] Case 3 Timeout...")
        page.locator("button[title*='Back to Application Queue']").click()
        page.wait_for_selector("text=Reviewer & Approver Workspace", timeout=10000)
        time.sleep(0.5)
        page.locator("tr:has-text('APP-2026-WARN-003')").locator("button:has-text('Inspect')").click()
        page.wait_for_selector("text=APP-2026-WARN-003", timeout=10000)
        time.sleep(0.5)
        page.click("button:has-text('F. Registries')")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_12_case3_registries_unavailable.png"))
        sign_out(page)

        # 4. Vendor Correction View
        print("[Desktop] Vendor view...")
        login(page, "vendor.mismatch@sharmaworks.in")
        page.wait_for_selector("text=Action Required from Vendor", timeout=12000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_13_vendor_clarification_view.png"))
        sign_out(page)

        # 5. Tokenized Invitation Public Screen
        print("[Desktop] Tokenized invite landing...")
        page.goto(f"{BASE_URL}/invite/demo-invitation-token-apex-2026")
        page.wait_for_selector("text=Vendor Onboarding Portal", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_14_invite_portal.png"))

        # 6. Admin Control Center
        print("[Desktop] Admin dashboard...")
        login(page, "admin@apex.com")
        page.wait_for_selector("text=Administrator Control Center", timeout=10000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "desktop_15_admin_control_center.png"))
        sign_out(page)

        context.close()

        # -------------------------------------------------------------
        # MOBILE AUDIT (375x812 iPhone / Mobile)
        # -------------------------------------------------------------
        print("\n=== Running Mobile Audit (375x812) ===")
        m_ctx = browser.new_context(viewport={"width": 375, "height": 812})
        m_page = m_ctx.new_page()

        # Mobile Login
        m_page.goto(f"{BASE_URL}/")
        m_page.wait_for_selector("input[type='email']", timeout=10000)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_01_login.png"))

        # Mobile Procurement
        login(m_page, "procurement@apex.com")
        m_page.wait_for_selector("text=Procurement & Onboarding Operations", timeout=10000)
        time.sleep(0.5)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_02_procurement_dash.png"))
        sign_out(m_page)

        # Mobile Reviewer Queue
        login(m_page, "reviewer@apex.com")
        m_page.wait_for_selector("text=Reviewer & Approver Workspace", timeout=10000)
        time.sleep(0.5)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_03_reviewer_queue.png"))

        # Mobile Reviewer Case 1
        m_page.locator("tr:has-text('APP-2026-CLEAN-001')").locator("button:has-text('Inspect')").click()
        m_page.wait_for_selector("text=APP-2026-CLEAN-001", timeout=10000)
        time.sleep(0.5)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_04_case1_workspace.png"))
        sign_out(m_page)

        # Mobile Vendor Clarification
        login(m_page, "vendor.mismatch@sharmaworks.in")
        m_page.wait_for_selector("text=Action Required from Vendor", timeout=12000)
        time.sleep(0.5)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_05_vendor_clarification.png"))
        sign_out(m_page)

        # Mobile Invite Portal
        m_page.goto(f"{BASE_URL}/invite/demo-invitation-token-apex-2026")
        m_page.wait_for_selector("text=Vendor Onboarding Portal", timeout=10000)
        time.sleep(0.5)
        m_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mobile_06_invite_portal.png"))

        m_ctx.close()
        browser.close()
        print("\nAll UX audit screenshots captured successfully in:", SCREENSHOT_DIR)

if __name__ == "__main__":
    run_audit()
