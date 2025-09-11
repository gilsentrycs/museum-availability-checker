"""
Chichu Art Museum availability checker (Playwright)

Checks the Benesse/Eventos Tokyo reservation page for openings for a
specific date and notifies you. Designed to be run via cron.

Requirements:
  pip install playwright python-dotenv
  playwright install

Usage:
  # 1) Copy this file to a folder
  # 2) Create a .env next to it (optional) and set variables below
  # 3) Run: python chichu_availability_checker.py

Environment variables (or edit defaults below):
  TARGET_URL         - Reservation page URL (default: the one provided)
  TARGET_DATE        - ISO date to look for, e.g. 2025-10-07
  HEADLESS           - '1' (default) for headless browser, '0' to watch
  TIMEOUT_MS         - Navigation timeout in ms (default 45000)

Notifications (optional; set any that you want):
  # Desktop notification (macOS / Linux libnotify)
  DESKTOP_NOTIFY     - '1' to enable, otherwise disabled

  # Telegram (bot)
  TELEGRAM_BOT_TOKEN - your bot token
  TELEGRAM_CHAT_ID   - your chat id

  # Simple email via SMTP (Gmail example; may require app password)
  EMAIL_FROM         - sender email
  EMAIL_TO           - recipient email
  SMTP_HOST          - default: smtp.gmail.com
  SMTP_PORT          - default: 587
  SMTP_USER          - username (often same as EMAIL_FROM)
  SMTP_PASS          - password or app password

What it looks for:
  - It tries to select the date picker for TARGET_DATE if present
  - Then it scans the page for text markers like 'Available', 'Sold out',
    or symbols often used by Japanese booking UIs: ○ (open), △ (few), × (full)
  - If it detects availability ("Available", '○', '△'), it triggers notification

You might need to tweak the selectors below if the site changes.
"""

import os
import re
import sys
import smtplib
from email.mime.text import MIMEText
from contextlib import suppress
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/176695?language=eng")
TARGET_URLS = os.getenv("TARGET_URLS", "")  # Comma-separated list of URLs
TARGET_DATE = os.getenv("TARGET_DATE", "2025-10-07")  # YYYY-MM-DD
HEADLESS = os.getenv("HEADLESS", "1") == "1"
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "45000"))

# Notification settings
DESKTOP_NOTIFY = os.getenv("DESKTOP_NOTIFY", "0") == "1"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or EMAIL_FROM
SMTP_PASS = os.getenv("SMTP_PASS")

# Only treat the explicit calendar symbols as positive.
 # Many pages include the words “Available/Availability” in legends/notes.
AVAILABILITY_POSITIVE = [
    r"[○◯]",   # open circle = open
    r"△",      # few left
]
AVAILABILITY_NEGATIVE = [
    r"Sold\s*out",
    r"Fully\s*booked",
    r"Unavailable",
    r"[×✕✖]",   # cross, full
]


def desktop_notify(title: str, message: str) -> None:
    if not DESKTOP_NOTIFY:
        return
    if sys.platform == "darwin":
        os.system(f"osascript -e 'display notification \"{message}\" with title \"{title}\"' || true")
    else:
        # Linux notify-send
        os.system(f"notify-send '{title}' '{message}' || true")


def telegram_notify(message: str) -> None:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    import urllib.parse, urllib.request
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }).encode()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    with suppress(Exception):
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)


def email_notify(subject: str, body: str) -> None:
    if not (EMAIL_FROM and EMAIL_TO and SMTP_PASS):
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    except Exception as e:
        print(f"[warn] email notify failed: {e}")


def looks_available(text: str) -> bool:
    # Positive beats negative; we check for explicit positives first
    for pat in AVAILABILITY_NEGATIVE:
        if re.search(pat, text, flags=re.I):
            return False
    for pat in AVAILABILITY_POSITIVE:
        if re.search(pat, text, flags=re.I):
            return True
    return False


def main() -> int:
    print(f"[info] Checking {TARGET_URL} for {TARGET_DATE}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(TARGET_URL, timeout=TIMEOUT_MS)

            # Try to interact with a date picker if present. The exact selectors may need adjustment.
            # Common patterns: input[type=date], aria labels, or a custom calendar grid.
            # We'll attempt a few strategies.
            with suppress(Exception):
                # Strategy 1: native date input
                date_input = page.query_selector('input[type="date"]')
                if date_input:
                    date_input.fill(TARGET_DATE)
                    page.wait_for_timeout(1000)

            with suppress(Exception):
                # Strategy 2: buttons that open calendar and then select the date cell
                # This is intentionally generic; adjust selectors if needed.
                if not page.query_selector('input[type="date"]'):
                    # open calendar
                    btn = page.query_selector('[aria-label*="calendar" i], button:has-text("Calendar")')
                    if btn:
                        btn.click()
                        page.wait_for_timeout(500)
                        # try to click the date cell by data attributes or text
                        yyyy, mm, dd = TARGET_DATE.split('-')
                        # try data-date="YYYY-MM-DD"
                        selector_try = [
                            f'[data-date="{TARGET_DATE}"]',
                            f'td[aria-label*="{int(dd)}" i]',
                            f'td:has-text("{int(dd)}")',
                            f'button:has-text("{int(dd)}")',
                        ]
                        for sel in selector_try:
                            with suppress(Exception):
                                el = page.query_selector(sel)
                                if el:
                                    el.click()
                                    page.wait_for_timeout(800)
                                    break

            # Wait a bit for any availability refresh
            page.wait_for_timeout(1500)

            # Scrape visible text
            full_text = page.inner_text("body")

            is_open = looks_available(full_text)
            print(f"[info] availability heuristic => {'AVAILABLE' if is_open else 'not available'}")

            if is_open:
                msg = (
                    f"Chichu Art Museum appears to have availability on {TARGET_DATE}.\n"
                    f"Book ASAP: {TARGET_URL}"
                )
                desktop_notify("Chichu tickets available!", msg)
                telegram_notify(msg)
                email_notify("Chichu tickets available!", msg)
            return 0
        except PlaywrightTimeoutError:
            print("[error] Page load timeout. Try increasing TIMEOUT_MS or using HEADLESS=0 to debug.")
            return 2
        except Exception as e:
            print(f"[error] {e}")
            return 3
        finally:
            context.close()
            browser.close()


# --- Update: multi-date testing + screenshots ---
# New features:
#  - Accept multiple dates via --dates 2025-10-01,2025-10-07 or TARGET_DATES env (comma separated)
#  - For each date: try to select it, then determine availability using
#    (a) specific cell state heuristics (aria-disabled/class/x/○/△) and
#    (b) a full-page text fallback.
#  - Save a screenshot per date under ./screenshots/DATE.png for manual verification.
#  - Exit code 0 but print a concise summary table at the end.

if __name__ == "__main__":
    # CLI wrapper for quick testing of two dates.
    import argparse
    parser = argparse.ArgumentParser(description="Chichu availability checker")
    parser.add_argument("--dates", help="Comma-separated ISO dates to check (YYYY-MM-DD)")
    args = parser.parse_args()

    dates = []
    if args.dates:
        dates = [d.strip() for d in args.dates.split(',') if d.strip()]
    elif os.getenv("TARGET_DATES"):
        dates = [d.strip() for d in os.getenv("TARGET_DATES").split(',') if d.strip()]
    else:
        # fallback to single TARGET_DATE
        dates = [TARGET_DATE]

    # Ensure screenshots folder exists
    os.makedirs("screenshots", exist_ok=True)

    results = []
    from playwright.sync_api import sync_playwright

    print(f"[info] Checking {len(dates)} date(s) at {TARGET_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(TARGET_URL, timeout=TIMEOUT_MS)
            page.wait_for_timeout(1200)

            # Handle popup/modal that needs to be dismissed first
            print("[info] Checking for popup/modal to dismiss...")
            popup_found = False
            try:
                popup_btn = page.query_selector('button:has-text("OK")')
                if popup_btn and popup_btn.is_visible():
                    print(f"[info] Found and clicking OK button")
                    popup_btn.click()
                    popup_found = True
                    page.wait_for_timeout(3000)  # Wait for popup to close and iframe to load
            except Exception as e:
                print(f"[debug] Popup handling error: {e}")
            
            if not popup_found:
                print("[info] No popup found or already dismissed")
            
            # Find the iframe calendar directly  
            print("[info] Looking for iframe calendar...")
            try:
                iframe = page.query_selector('#bsvCalendarIframe, iframe[src*="calendar"]')
                if iframe:
                    iframe_src = iframe.get_attribute('src') or 'no src'
                    print(f"[info] Found iframe: {iframe_src}")
                    
                    # Switch to iframe to access calendar
                    iframe_content = iframe.content_frame()
                    if iframe_content:
                        print("[info] Successfully switched to iframe")
                        # Wait for calendar content to load
                        iframe_content.wait_for_timeout(2000)
                        
                        # Check current month and navigate to October if needed
                        try:
                            iframe_body_text = iframe_content.inner_text('body')
                            print(f"[debug] Full iframe text sample: {iframe_body_text[:300]}...")
                            month_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}\b'
                            month_match = re.search(month_pattern, iframe_body_text, re.I)
                            if month_match:
                                current_month_text = month_match.group()
                                print(f"[debug] Current month in iframe: {current_month_text}")
                                
                                # If we're in September 2025, click next to get to October 2025
                                if "september 2025" in current_month_text.lower():
                                    print("[info] Currently in September 2025, navigating to October...")
                                    next_btn = iframe_content.query_selector('img[src*="arrow_next_calendar.svg"]')
                                    if next_btn:
                                        next_btn.click()
                                        iframe_content.wait_for_timeout(3000)  # Wait longer for month change
                                        print("[info] Clicked next month button")
                                        
                                        # Verify we're now in October
                                        updated_text = iframe_content.inner_text('body')
                                        updated_match = re.search(month_pattern, updated_text, re.I)
                                        if updated_match:
                                            current_month_text = updated_match.group()
                                            print(f"[debug] After navigation, current month: {current_month_text}")
                                            # Set a flag to indicate we've navigated
                                            page._navigated_to_october = True
                                    else:
                                        print("[warn] Could not find next month button")
                                elif "october 2025" in current_month_text.lower():
                                    print("[info] Already in October 2025")
                                    page._navigated_to_october = True
                            else:
                                print("[debug] No month pattern found in iframe text")
                        except Exception as e:
                            print(f"[debug] Error with month navigation: {e}")
                        
                        page._iframe_calendar = iframe_content
                    else:
                        print("[warn] Could not access iframe content")
                else:
                    print("[warn] No iframe found")
            except Exception as e:
                print(f"[debug] Iframe access error: {e}")

            for d in dates:
                print(f"[info] Processing date: {d}")
                
                # Use iframe calendar page if available
                calendar_page = getattr(page, '_iframe_calendar', page)
                
                # Parse target date
                target_year, target_month, target_day = d.split('-')
                target_year, target_month, target_day = int(target_year), int(target_month), int(target_day)
                
                print(f"[info] Looking for {target_year}-{target_month:02d}-{target_day:02d}")
                
                # Check what month is currently displayed
                try:
                    month_text = calendar_page.inner_text('body')
                    print(f"[debug] Calendar text preview: {month_text[:200]}...")
                    
                    # Only navigate if we haven't already navigated to October
                    if hasattr(page, '_navigated_to_october') and page._navigated_to_october:
                        print(f"[info] Already navigated to October, skipping additional navigation")
                    elif "October 2025" in month_text and target_month == 10 and target_year == 2025:
                        print(f"[info] Already showing October 2025")
                    else:
                        print(f"[info] Current calendar shows different month, trying to navigate...")
                        # Look for navigation buttons based on the HTML structure you provided
                        next_arrow = calendar_page.query_selector('img[src*="arrow_next_calendar.svg"]')
                        prev_arrow = calendar_page.query_selector('img[src*="arrow_prev_calendar.svg"]')
                        
                        if next_arrow:
                            print("[info] Found next arrow, clicking to navigate to October")
                            next_arrow.click()
                            calendar_page.wait_for_timeout(2000)
                        elif prev_arrow:
                            print("[info] Found prev arrow but no next - might need different logic")
                        
                except Exception as e:
                    print(f"[debug] Month detection error: {e}")
                
                # Find the specific date button using the exact structure from HTML
                verdict = "UNSURE"
                evidence = []
                
                try:
                    # Look for the day button with the specific structure - try multiple approaches
                    day_selectors = [
                        f'.title-day:has-text("{target_day}")',  # Find the span with day number
                        f'button:has-text("{target_day}")',      # Try button directly
                        f'span:has-text("{target_day}")',        # Try span directly
                    ]
                    
                    day_element = None
                    for selector in day_selectors:
                        day_element = calendar_page.query_selector(selector)
                        if day_element:
                            print(f"[debug] Found day element using: {selector}")
                            break
                    
                    if day_element:
                        # Get the parent button - walk up the DOM to find the button
                        button_element = day_element
                        
                        # Try to find parent button using different methods
                        if day_element.evaluate('el => el.tagName').lower() != 'button':
                            # Try xpath to find ancestor button
                            try:
                                button_element = day_element.query_selector('xpath=ancestor::button')
                            except:
                                # Try evaluating to walk up DOM manually
                                button_element = calendar_page.evaluate('''
                                    (element) => {
                                        let current = element;
                                        while (current && current.tagName !== 'BUTTON') {
                                            current = current.parentElement;
                                        }
                                        return current;
                                    }
                                ''', day_element)
                        
                        if button_element:
                            button_class = button_element.get_attribute('class') or ''
                            button_html = button_element.inner_html()[:200]  # Get some HTML for debugging
                            
                            # Look for availability images within the button
                            available_img = button_element.query_selector('img[src*="available.svg"]')
                            sold_out_img = button_element.query_selector('img[src*="sold_out.svg"]')
                            few_left_img = button_element.query_selector('img[src*="only_one_left.svg"]')
                            
                            print(f"[debug] Found date {target_day}, button class: '{button_class}'")
                            print(f"[debug] Button HTML preview: {button_html}")
                            print(f"[debug] Images: available={available_img is not None}, sold_out={sold_out_img is not None}, few_left={few_left_img is not None}")
                            
                            # Determine availability based on the structure we saw
                            if available_img:
                                verdict = "AVAILABLE"
                                evidence.append("available.svg found")
                                print(f"[debug] ✅ Date {target_day} is AVAILABLE (available.svg)")
                            elif few_left_img:
                                verdict = "AVAILABLE"  # Few left is still available
                                evidence.append("only_one_left.svg found")
                                print(f"[debug] ✅ Date {target_day} is AVAILABLE (few left)")
                            elif sold_out_img:
                                verdict = "UNAVAILABLE"
                                evidence.append("sold_out.svg found")
                                print(f"[debug] ❌ Date {target_day} is UNAVAILABLE (sold out)")
                            elif 'sold-out-layout' in button_class:
                                verdict = "UNAVAILABLE"
                                evidence.append("sold-out-layout class")
                                print(f"[debug] ❌ Date {target_day} is UNAVAILABLE (sold-out-layout)")
                            elif 'pointer-none' in button_class:
                                verdict = "UNAVAILABLE"
                                evidence.append("pointer-none class (closed)")
                                print(f"[debug] ❌ Date {target_day} is UNAVAILABLE (closed/pointer-none)")
                            elif 'day-active' in button_class:
                                # Need to check further - day-active alone isn't conclusive
                                if 'aval' in button_html:
                                    verdict = "AVAILABLE"
                                    evidence.append("day-active + aval found")
                                    print(f"[debug] ✅ Date {target_day} is AVAILABLE (day-active + aval)")
                                else:
                                    verdict = "UNSURE"
                                    evidence.append("day-active but no clear availability indicator")
                                    print(f"[debug] ❓ Date {target_day} status unclear (day-active only)")
                            else:
                                evidence.append(f"unknown button state: {button_class}")
                                print(f"[debug] ❓ Date {target_day} unknown state: {button_class}")
                        else:
                            evidence.append("found day element but no parent button")
                            print(f"[debug] Found day {target_day} element but couldn't find parent button")
                    else:
                        evidence.append("date element not found")
                        print(f"[debug] Could not find date element for day {target_day}")
                        
                        # Debug: show what days are available
                        all_days = calendar_page.query_selector_all('.title-day')
                        available_days = [day.inner_text() for day in all_days if day.inner_text().strip().isdigit()]
                        print(f"[debug] Available days in calendar: {available_days}")
                        
                except Exception as e:
                    print(f"[debug] Date detection error: {e}")
                    evidence.append(f"error: {e}")

                # Screenshot for manual validation
                safe_d = d.replace('-', '_')
                try:
                    calendar_page.screenshot(path=f"screenshots/{safe_d}.png", full_page=True)
                except:
                    page.screenshot(path=f"screenshots/{safe_d}.png", full_page=True)

                results.append({"date": d, "verdict": verdict, "evidence": "; ".join(evidence)[:300]})

            # Print a compact summary
            print("""
Summary:
Date          Status        Evidence
------------  ------------  -------------------------------------------
""")
            for r in results:
                print(f"{r['date']}  {r['verdict']:<12}  {r['evidence']}")

        finally:
            context.close()
            browser.close()
