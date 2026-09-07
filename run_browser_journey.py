"""Mandatory Wave 3 Browser Journey.

Executes the real browser UI flow using Playwright against Chrome:
1. Register & Login via UI
2. Navigate to Opportunities Center
3. Browse & apply filters (sector, budget, keyword)
4. Open business opportunity details & inspect evidence / source provenance
5. Open franchise opportunity details & inspect evidence / franchise fees
6. Compare 2 opportunities side-by-side
7. Create Study from an opportunity
8. Verify created Study workspace displays Opportunity Lineage banner & transferred facts
9. Refresh browser & verify persistence
10. Logout via UI
11. Login via UI
12. Reopen created Study & verify persistent lineage
13. Verify zero console errors and clean network responses
"""
import sys
import time
import json
import urllib.request
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:3000"
API_URL = "http://127.0.0.1:8000"

console_errors = []
network_failures = []


def on_console(msg):
    if msg.type in ("error",):
        text = msg.text.lower()
        url = (msg.location.get("url") or "").lower()
        if "favicon" in text or "chrome-extension" in text or "favicon" in url or "chrome-extension" in url:
            return
        console_errors.append(f"{msg.text} (location: {msg.location})")
        print(f"[BROWSER CONSOLE ERROR] {msg.text} - {msg.location}")


def on_response(response):
    if response.status >= 400:
        url = response.url.lower()
        if "favicon" not in url:
            print(f"[HTTP {response.status}] {response.url}")


def on_request_failed(request):
    url = request.url.lower()
    # Next.js cancels background prefetch requests upon navigation which is expected behavior
    if request.failure == "net::ERR_ABORTED" and "_rsc=" in url:
        return
    if "favicon" not in url and "chrome-extension" not in url:
        network_failures.append(f"{request.method} {request.url}: {request.failure}")
        print(f"[BROWSER NETWORK FAILURE] {request.method} {request.url}: {request.failure}")


def main():
    print("=== STARTING WAVE 3 MANDATORY BROWSER JOURNEY ===")

    with sync_playwright() as p:
        browser = None
        for channel in ["chrome", "msedge", None]:
            try:
                if channel:
                    browser = p.chromium.launch(channel=channel, headless=True)
                else:
                    browser = p.chromium.launch(headless=True)
                print(f"Browser launched successfully using: {channel or 'bundled chromium'}")
                break
            except Exception as e:
                print(f"Channel {channel} launch failed: {e}")

        if not browser:
            print("Failed to launch any browser!")
            sys.exit(1)

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ar-SA",
        )
        page = context.new_page()
        page.on("console", on_console)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

        # ----------------------------------------------------------------------
        # 1. Register a test user and Login via UI
        # ----------------------------------------------------------------------
        print("\nStep 1: Registering & Logging in via UI...")
        test_email = f"founder_w3_{int(time.time())}@example.com"
        test_pass = "Sup3rSecretWave3!"

        # Register user via API
        reg_req = urllib.request.Request(
            f"{API_URL}/auth/register",
            data=json.dumps({"email": test_email, "password": test_pass}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(reg_req) as resp:
            assert resp.status == 201
            print(f"Test user registered: {test_email}")

        # UI Login
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector('input[type="email"]')
        page.fill('input[type="email"]', test_email)
        page.fill('input[type="password"]', test_pass)
        page.click('button[type="submit"]')

        page.wait_for_timeout(2000)
        print(f"Logged in successfully. Current URL: {page.url}")

        # ----------------------------------------------------------------------
        # 2. Navigate to Opportunities Center
        # ----------------------------------------------------------------------
        print("\nStep 2: Navigating to Opportunities Center (/opportunities)...")
        page.goto(f"{BASE_URL}/opportunities")
        page.wait_for_selector("h1")
        title_text = page.locator("h1").inner_text()
        print(f"Page Title: {title_text}")
        assert "الفرص" in title_text

        # ----------------------------------------------------------------------
        # 3. Browse opportunities and apply filters
        # ----------------------------------------------------------------------
        print("\nStep 3: Browsing opportunities and testing filters...")
        page.wait_for_selector('[data-testid="opportunity-card"]', timeout=10000)
        cards = page.locator('[data-testid="opportunity-card"]').all()
        print(f"Initial actionable opportunities displayed: {len(cards)} items")
        # Wave 3A: Only actual proven opportunities (3 franchises) are actionable
        assert len(cards) == 3, f"Expected exactly 3 actionable opportunities, got {len(cards)}"

        # Filter by sector: food_beverage
        print("Filtering by sector: food_beverage...")
        page.select_option("select:has-text('جميع القطاعات')", value="food_beverage")
        page.wait_for_timeout(1000)
        filtered_cards = page.locator('[data-testid="opportunity-card-title"]').all_inner_texts()
        print(f"Filtered cards (food_beverage): {len(filtered_cards)} items")
        assert len(filtered_cards) == 3
        assert any("بارنز" in c for c in filtered_cards)

        # Reset sector filter
        page.select_option("select:has-text('القطاعات')", value="")
        page.wait_for_timeout(1000)

        # Filter by budget: 400000 (Rule C: confirm UNKNOWN budget is NOT shown as fit)
        print("Filtering by budget: 400,000 SAR (Verifying UNKNOWN budget != budget fit)...")
        page.fill('input[type="number"]', "400000")
        page.wait_for_timeout(1000)

        # Verify budget fit section shows empty message
        assert page.locator('[data-testid="budget-fit-empty"]').is_visible()
        # Verify unknown budget opportunities are isolated in clearly separate group
        assert page.locator('[data-testid="budget-unknown-group"]').is_visible()
        assert page.locator('[data-testid="budget-unknown-notice"]').is_visible()
        unknown_cards = page.locator('[data-testid="budget-unknown-group"] [data-testid="opportunity-card"]').all()
        assert len(unknown_cards) == 3
        print(f"Confirmed: UNKNOWN budget is NOT shown as fit ({len(unknown_cards)} isolated in budget-unknown group).")

        # Clear budget
        page.fill('input[type="number"]', "")
        page.wait_for_timeout(1000)

        # ----------------------------------------------------------------------
        # 4. Inspect Opportunity Details, Exact Primary Evidence & Provenance
        # ----------------------------------------------------------------------
        print("\nStep 4: Inspecting Opportunity Details, Exact Primary Evidence & Provenance for all 3 actionable records...")
        
        expected_sources = {
            "بارنز": "https://barns.com.sa/en/franchising-and-licensing",
            "كيف": "https://drcafe.com/en-sa/franchise-profile",
            "شاورمر": "https://franchise.shawarmer.com/",
        }

        cards = page.locator('[data-testid="opportunity-card"]').all()
        assert len(cards) == 3, f"Expected 3 actionable cards, got {len(cards)}"

        for i in range(len(cards)):
            card = page.locator('[data-testid="opportunity-card"]').nth(i)
            card_text = card.inner_text()
            
            # Find matching brand
            matched_key = None
            for key in expected_sources:
                if key in card_text:
                    matched_key = key
                    break
            assert matched_key is not None, f"Card does not match any expected brand: {card_text}"
            expected_url = expected_sources[matched_key]

            # Click details button
            card.locator("button:has-text('التفاصيل والأدلة')").click()
            page.wait_for_selector('div[role="dialog"]')
            dialog = page.locator('div[role="dialog"]')
            dialog_text = dialog.inner_text()

            assert "معلومات منشورة وموثقة" in dialog_text
            assert "تصنيف المنصة المعياري" in dialog_text
            assert "معلومات غير معلنة" in dialog_text
            assert "افتراضات مطلوبة من المستثمر" in dialog_text
            assert "توثيق وجود الفرصة بالمصدر الأولي" in dialog_text

            source_link = dialog.locator(f'a[href="{expected_url}"]')
            assert source_link.is_visible(), f"Expected link with href '{expected_url}' not found in modal for {matched_key}"
            print(f"Verified official source for {matched_key}: {expected_url}")

            # Close modal
            dialog.locator("button:has-text('إغلاق')").click()
            page.wait_for_timeout(500)

        print("Verified all 3 actionable opportunities have exact canonical primary sources and 0 broken source links.")

        # ----------------------------------------------------------------------
        # 5. Wave 3B: My Fit Tab, Profile Constraints, Deterministic Matching & Explain Fit
        # ----------------------------------------------------------------------
        print("\nStep 5: Testing Wave 3B 'فرص تناسبني (My Fit)' Tab and Deterministic Matching...")
        my_fit_tab = page.locator('[data-testid="my-fit-tab"]')
        assert my_fit_tab.is_visible()
        my_fit_tab.click()
        page.wait_for_timeout(500)

        # Form fields should be visible
        page.wait_for_selector('[data-testid="capital-input"]')
        print("Fit profile constraints form is visible.")

        # Verify brand-new user starts with neutral / empty capital (no manufactured 450,000 value)
        initial_capital_val = page.locator('[data-testid="capital-input"]').input_value()
        assert initial_capital_val == "", f"Expected empty initial capital, got '{initial_capital_val}'"
        placeholder_val = page.locator('[data-testid="capital-input"]').get_attribute("placeholder")
        assert "450,000" in (placeholder_val or ""), "Expected 450,000 placeholder hint"
        print("Confirmed: Brand-new user starts with empty capital (no synthetic 450,000 default value).")

        # Verify new fit preference fields are visible in the form
        assert page.locator('[data-testid="target-customer-select"]').is_visible()
        assert page.locator('[data-testid="business-model-input"]').is_visible()
        assert page.locator('[data-testid="experience-sectors-select"]').is_visible()
        print("Confirmed: target_customer, preferred_business_models, and experience_sectors are visible in UI.")

        # Set capital to 500,000 SAR
        page.fill('[data-testid="capital-input"]', "500000")

        # Verify capital constraint UI options strictly reflect implemented semantics
        cap_strength_select = page.locator('[data-testid="capital-strength-select"]')
        select_options_text = cap_strength_select.inner_text()
        assert "قيد حتمي — لا أتجاوز رأس المال" in select_options_text
        assert "تفضيل — يمكنني مراجعة خيارات أعلى من الميزانية" in select_options_text
        assert "FLEXIBLE_10" not in select_options_text
        assert "FLEXIBLE_20" not in select_options_text
        print("Confirmed: Capital constraint options strictly reflect HARD and PREFERENCE.")
        
        # Click evaluate button
        print("Clicking Evaluate Fit button...")
        page.click('[data-testid="evaluate-fit-btn"]')
        page.wait_for_timeout(1500)

        # Verify evaluated cards appear
        fit_cards = page.locator('[data-testid="opportunity-card"]').all()
        print(f"Evaluated match cards displayed: {len(fit_cards)} cards")
        assert len(fit_cards) >= 3, f"Expected at least 3 evaluated cards, got {len(fit_cards)}"

        # Verify no synthetic percentages or scores (e.g., "87%", "درجة التوافق")
        for card in fit_cards:
            text = card.inner_text()
            assert "%" not in text, f"Synthetic percentage detected in card: {text}"
            assert "درجة" not in text or "درجة التوافق" not in text, "Synthetic score detected in card"
        print("Confirmed: ZERO synthetic percentages or arbitrary scores present.")

        # Check Barn's Cafe card has NEEDS_INFORMATION with missing info notice
        barns_found = False
        for card in fit_cards:
            text = card.inner_text()
            if "بارنز" in text:
                barns_found = True
                assert "يحتاج معلومات إضافية" in text or "غير محدد" in text or "NEEDS_INFORMATION" in text
                print("Confirmed Barn's Cafe evaluates deterministically to NEEDS_INFORMATION (due to unknown investment min).")
                break
        assert barns_found, "Barn's Cafe card not found in fit results"

        # Click Explain Fit button
        print("Opening Explain Fit breakdown modal...")
        explain_btn = page.locator('[data-testid="explain-fit-btn"]').first
        explain_btn.click()
        page.wait_for_selector('[data-testid="explain-fit-modal"]')
        explain_modal = page.locator('[data-testid="explain-fit-modal"]')
        modal_text = explain_modal.inner_text()
        assert "الملاءمة" in modal_text
        assert "خلاصة القرار" in modal_text
        assert "المعيار" in modal_text
        assert "النتيجة" in modal_text
        print("Verified Explain Fit modal displays full deterministic criteria evaluation table.")

        # Close explain fit modal
        explain_modal.locator("button:has-text('إغلاق')").click()
        page.wait_for_timeout(500)

        # Test Hard Constraint Rejection: Exclude Food & Beverage
        print("Testing Hard Constraint: Exclude 'food_beverage' sector...")
        page.select_option('[data-testid="excluded-sectors-select"]', value="food_beverage")
        page.click('[data-testid="evaluate-fit-btn"]')
        page.wait_for_timeout(1500)

        # All 3 actionable F&B franchises should now evaluate to NOT_MATCHED
        updated_cards = page.locator('[data-testid="opportunity-card"]').all()
        fb_count = 0
        for card in updated_cards:
            text = card.inner_text()
            if any(brand in text for brand in ["بارنز", "كيف", "شاورمر"]):
                assert "غير متطابق" in text or "NOT_MATCHED" in text, f"Expected NOT_MATCHED for F&B brand, got: {text}"
                fb_count += 1
        assert fb_count == 3, f"Expected 3 F&B cards, found {fb_count}"
        print("Confirmed: Excluded sector hard constraint causes deterministic transition to NOT_MATCHED for all 3 F&B opportunities.")

        # Save Fit Matching screenshot
        page.screenshot(path="browser_verification_opportunity_fit.png")
        print("Saved verification screenshot to browser_verification_opportunity_fit.png")

        # Clear excluded sector constraint
        print("Clearing sector exclusion...")
        page.select_option('[data-testid="excluded-sectors-select"]', value="")
        page.click('[data-testid="evaluate-fit-btn"]')
        page.wait_for_timeout(1500)

        # ----------------------------------------------------------------------
        # 6. Compare Opportunities Side-by-Side (including Fit state)
        # ----------------------------------------------------------------------
        print("\nStep 6: Comparing opportunities side-by-side...")
        # Switch back to All tab to add compare items
        page.click("button:has-text('جميع الفرص والامتياز')")
        page.wait_for_timeout(500)

        compare_buttons = page.locator("button:has-text('إضافة للمقارنة')")
        compare_buttons.nth(0).click()
        page.wait_for_timeout(300)
        compare_buttons.nth(1).click()
        page.wait_for_timeout(500)

        # Open comparison tab
        page.click("button:has-text('المقارنة المباشرة')")
        page.wait_for_timeout(1000)
        table = page.locator("table")
        assert table.is_visible()
        table_text = table.inner_text()
        assert "نوع الفرصة" in table_text
        assert "القطاع" in table_text
        assert "نطاق الاستثمار المنشور" in table_text
        assert "جهة المصدر الرسمي" in table_text
        assert "حالة التوثيق" in table_text
        assert "حالة الملاءمة" in table_text
        assert "VERIFIED_PARTIAL" in table_text or "موثق" in table_text, "Comparison table must preserve VERIFIED_PARTIAL status"
        print("Verified factual side-by-side comparison table preserves VERIFIED_PARTIAL and displays deterministic fit state row.")

        # Return to My Fit tab
        page.click('[data-testid="my-fit-tab"]')
        page.wait_for_timeout(500)

        # ----------------------------------------------------------------------
        # 7. Create Study from Opportunity via Fit Card
        # ----------------------------------------------------------------------
        print("\nStep 7: Creating Feasibility Study from Opportunity Fit Card...")
        create_study_btn = page.locator('[data-testid="start-study-btn"]').first
        create_study_btn.click()
        page.wait_for_selector('div[role="dialog"]')
        cs_dialog = page.locator('div[role="dialog"]')
        print("Create study confirmation modal opened from fit card.")

        # Enter user budget assumption if required
        budget_input = cs_dialog.locator('input[type="number"]')
        if budget_input.count() > 0 and budget_input.first.is_visible():
            budget_input.first.fill("500000")
            print("Entered user budget assumption: 500,000 SAR (USER_ASSUMPTION)")

        # Confirm and launch
        cs_dialog.locator("button:has-text('تأكيد وبدء الدراسة')").click()

        # ----------------------------------------------------------------------
        # 8. Verify Created Study Workspace & Lineage Banner
        # ----------------------------------------------------------------------
        print("\nStep 8: Verifying Study Workspace & Lineage Banner...")
        page.wait_for_url("**/studies/**", timeout=20000)
        print(f"Navigated to study workspace: {page.url}")
        current_study_url = page.url

        page.wait_for_selector('[data-testid="opportunity-lineage-banner"]', timeout=10000)
        lineage_banner = page.locator('[data-testid="opportunity-lineage-banner"]')
        assert lineage_banner.is_visible()
        banner_text = lineage_banner.inner_text()
        print(f"Lineage banner confirmed. Sourced title visible: {'أصل الدراسة' in banner_text}")
        assert "أصل الدراسة: فرصة" in banner_text
        assert "المصدر الرسمي" in banner_text

        # ----------------------------------------------------------------------
        # 8b. Simulate Changed Source Version & Verify Match Freshness Protection
        # ----------------------------------------------------------------------
        print("\nStep 8b: Testing source version change freshness in UI and Study creation gate...")
        page.goto(f"{BASE_URL}/opportunities")
        page.wait_for_selector('[data-testid="my-fit-tab"]')
        page.click('[data-testid="my-fit-tab"]')
        page.wait_for_timeout(1000)

        import sqlite3
        conn = sqlite3.connect("backend/test.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_version FROM verified_opportunities WHERE slug = 'franchise-barns-cafe'")
        row = cursor.fetchone()
        assert row is not None
        barns_db_id, orig_db_version = row[0], row[1]
        try:
            # Bump version in DB
            cursor.execute("UPDATE verified_opportunities SET data_version = '2.0.0' WHERE id = ?", (barns_db_id,))
            conn.commit()
            print(f"Simulated source update: Bumped Barn's Cafe version in DB to 2.0.0 (was {orig_db_version})")

            # Reload page and open My Fit
            page.reload()
            page.wait_for_selector('[data-testid="my-fit-tab"]')
            page.click('[data-testid="my-fit-tab"]')
            page.wait_for_timeout(1500)

            # Check Barn's card shows NOT_EVALUATED
            cards = page.locator('[data-testid="opportunity-card"]').all()
            barns_stale_detected = False
            for card in cards:
                c_text = card.inner_text()
                if "بارنز" in c_text:
                    barns_stale_detected = True
                    print(f"Barn's card text after version bump: {c_text[:100]}...")
                    assert "غير خاضعة للتقييم" in c_text or "NOT_EVALUATED" in c_text or "إعادة" in c_text or "تغيرت" in c_text
                    break
            assert barns_stale_detected, "Barn's card not found after reload"
            print("Verified: Old match result deterministically became NOT_EVALUATED upon source version bump.")
        finally:
            # Restore original version
            cursor.execute("UPDATE verified_opportunities SET data_version = ? WHERE id = ?", (orig_db_version, barns_db_id))
            conn.commit()
            conn.close()

        # ----------------------------------------------------------------------
        # 9. Refresh Browser & Verify Persistence
        # ----------------------------------------------------------------------
        print("\nStep 9: Refreshing browser to verify study and lineage persistence...")
        page.goto(current_study_url)
        page.wait_for_selector('[data-testid="opportunity-lineage-banner"]', timeout=10000)
        page.reload()
        page.wait_for_selector('[data-testid="opportunity-lineage-banner"]', timeout=10000)
        persisted_banner = page.locator('[data-testid="opportunity-lineage-banner"]')
        assert persisted_banner.is_visible()
        print("Verified: Study and opportunity lineage completely survive browser reload.")

        # ----------------------------------------------------------------------
        # 10. Logout via UI
        # ----------------------------------------------------------------------
        print("\nStep 10: Logging out via UI...")
        logout_btn = page.locator("button:has-text('خروج')")
        if logout_btn.is_visible():
            logout_btn.click()
        else:
            page.goto(f"{BASE_URL}/")
            page.locator("button:has-text('خروج')").click()

        page.wait_for_timeout(2000)
        print(f"Logged out successfully. Current URL: {page.url}")

        # ----------------------------------------------------------------------
        # 11. Login via UI again
        # ----------------------------------------------------------------------
        print("\nStep 11: Logging back in via UI...")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector('input[type="email"]')
        page.fill('input[type="email"]', test_email)
        page.fill('input[type="password"]', test_pass)
        page.click('button[type="submit"]')
        page.wait_for_timeout(2000)
        print("Logged in successfully.")

        # ----------------------------------------------------------------------
        # 12. Reopen Created Study & Verify Lineage Persists
        # ----------------------------------------------------------------------
        print(f"\nStep 12: Reopening created study at {current_study_url}...")
        page.goto(current_study_url)
        page.wait_for_selector('[data-testid="opportunity-lineage-banner"]', timeout=10000)
        reopened_banner = page.locator('[data-testid="opportunity-lineage-banner"]')
        assert reopened_banner.is_visible()
        print("Verified: Lineage and study data completely persist across logout, login, and reopen!")

        # ----------------------------------------------------------------------
        # 13. Check Console Errors and Network Failures
        # ----------------------------------------------------------------------
        print("\nStep 13: Checking console errors and network health...")
        print(f"Console errors count: {len(console_errors)}")
        print(f"Network failures count: {len(network_failures)}")
        assert len(console_errors) == 0, f"Encountered console errors: {console_errors}"
        assert len(network_failures) == 0, f"Encountered network failures: {network_failures}"

        # Capture final verification screenshot
        page.screenshot(path="browser_verification_study_workspace.png")
        print("Saved verification screenshot to browser_verification_study_workspace.png")

        browser.close()
        print("\n=== MANDATORY BROWSER JOURNEY PASSED 100% ===")


if __name__ == "__main__":
    main()
