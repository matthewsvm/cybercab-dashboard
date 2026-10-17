"""Load the Streamlit Community Cloud app headlessly; wake it if it is asleep."""
import os, sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = os.environ.get("APP_URL", "https://cybercab-fleet-tracker.streamlit.app")
WAKE = "Yes, get this app back up"

def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        try:
            resp = page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            print(f"FAIL: page did not load: {e}"); sys.exit(1)
        print(f"HTTP status: {resp.status if resp else 'n/a'}")
        page.wait_for_timeout(15_000)  # let the sleep page / app shell render
        btn = page.get_by_role("button", name=WAKE)
        if btn.count() > 0:
            print("STATUS: app was ASLEEP - clicking wake button")
            btn.first.click()
            page.wait_for_timeout(60_000)
            still = page.get_by_role("button", name=WAKE).count() > 0
            print("After wake: " + ("wake button still visible" if still else "wake button gone (app booting/loaded)"))
        else:
            print("STATUS: app was AWAKE (no wake button)")
        b.close()

if __name__ == "__main__":
    main()
