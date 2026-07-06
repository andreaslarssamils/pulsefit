"""End-to-end newsletter subscribe via footer form; captures toast.
NOT committed. Requires the dev server running on 127.0.0.1:8000.

    .venv/bin/python screenshots/capture_newsletter.py
"""
import os

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = os.path.dirname(os.path.abspath(__file__))
EMAIL = "andreas.larssamils+pulsefit-newsletter-test@gmail.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={
            "width": 1280,
            "height": 800},
        device_scale_factor=2)
    page = ctx.new_page()

    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.fill("footer input[name=email]", EMAIL)
    page.click("footer button:has-text('Subscribe')")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(600)

    # Viewport shot (not full-page) so the toast at the top of <main> is
    # prominent.
    page.screenshot(
        path=os.path.join(
            OUT,
            "21b-newsletter-success-toast.png"),
        full_page=False)
    print("captured 21b-newsletter-success-toast.png")
    try:
        print(
            "TOAST TEXT:",
            page.locator(".toast").first.inner_text(
                timeout=3000))
    except Exception as e:  # noqa: BLE001
        print("no .toast found:", e)

    browser.close()
