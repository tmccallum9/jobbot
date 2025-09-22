import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
KELLOGG_EMAIL = os.getenv("KELLOGG_EMAIL")
KELLOGG_PASS = os.getenv("KELLOGG_PASS")
NETID = os.getenv("KELLOGG_NETID")
PASSWORD = os.getenv("KELLOGG_PASS")

# Use existing CMS credentials if Handshake-specific ones aren't available
if not KELLOGG_EMAIL:
    KELLOGG_EMAIL = os.getenv("KELLOGG_NETID") + "@kellogg.northwestern.edu"
if not KELLOGG_PASS:
    KELLOGG_PASS = os.getenv("KELLOGG_PASS")

assert NETID, "❌ KELLOGG_NETID not found in .env"
assert PASSWORD, "❌ KELLOGG_PASS not found in .env"


def debug_page_structure(page):
    """Debug function to inspect the page structure"""
    print("🔍 DEBUGGING PAGE STRUCTURE:")

    # Check for job listings
    job_links = page.query_selector_all("a[href*='/job-search/']")
    print(f"🔍 Found {len(job_links)} job links")

    # Check for different possible selectors
    possible_selectors = [
        "a[href*='/job-search/']",
        "a[role='button']",
        ".sc-jKQSiE",
        "a[aria-label*='Product']",
        "a[aria-label*='Intern']"
    ]

    for selector in possible_selectors:
        elements = page.query_selector_all(selector)
        print(f"🔍 Selector '{selector}': {len(elements)} elements found")
        if len(elements) > 0:
            # Print first few elements
            for i, el in enumerate(elements[:3]):
                text = el.inner_text().strip()
                aria_label = el.get_attribute("aria-label") or ""
                href = el.get_attribute("href") or ""
                if text or aria_label:
                    print(f"  [{i+1}] Text: '{text[:50]}...'")
                    print(f"      Aria-label: '{aria_label[:50]}...'")
                    print(f"      Href: '{href[:50]}...'")


def extract_job_info_from_page(page, job_url):
    """Extract detailed job information by visiting the job page"""
    try:
        # Navigate to the job page
        page.goto(job_url)
        page.wait_for_timeout(2000)

        # Extract company name
        company = "Unknown"
        company_selectors = [
            "[data-testid*='company']",
            "[data-testid*='employer']",
            "h3:has-text('Company')",
            "h4:has-text('Company')",
            ".company-name",
            ".employer-name",
            "a[href*='/employers/']",
            "span:has-text('Company') + *",
            "div:has-text('Company') + *"
        ]

        for selector in company_selectors:
            try:
                company_el = page.query_selector(selector)
                if company_el:
                    company_text = company_el.inner_text().strip()
                    if company_text and len(company_text) < 100:
                        company = company_text
                        break
            except:
                continue

        # Extract location
        location = "N/A"
        location_selectors = [
            "[data-testid*='location']",
            "h3:has-text('Location')",
            "h4:has-text('Location')",
            ".location",
            ".job-location",
            "span:has-text('Location') + *",
            "div:has-text('Location') + *",
            "[class*='location']"
        ]

        for selector in location_selectors:
            try:
                location_el = page.query_selector(selector)
                if location_el:
                    location_text = location_el.inner_text().strip()
                    if location_text and len(location_text) < 100:
                        location = location_text
                        break
            except:
                continue

        return company, location

    except Exception as e:
        print(f"❌ Error extracting job details from page: {e}")
        return "Unknown", "N/A"


def extract_job_info(job_element, page=None):
    """Extract job information from a job link element"""
    try:
        # Get the aria-label which contains the job title
        aria_label = job_element.get_attribute("aria-label") or ""
        href = job_element.get_attribute("href") or ""

        # Extract job title from aria-label
        title = aria_label.replace("View ", "").strip()

        # Build full URL
        if href.startswith("/"):
            url = f"https://app.joinhandshake.com{href}"
        else:
            url = href

        # Extract company and location from the job page if page is provided
        company = "Unknown"
        location = "N/A"

        if page:
            company, location = extract_job_info_from_page(page, url)

        return {
            "title": title,
            "company": company,
            "location": location,
            "url": url
        }
    except Exception as e:
        print(f"❌ Error extracting job info: {e}")
        return None


def login_and_scrape():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Step 1: Navigate to Handshake login
            print("🔐 Step 1: Navigating to Handshake login...")
            page.goto("https://app.joinhandshake.com/login")
            page.wait_for_timeout(3000)

            # Debug: Check what's on the page
            print("🔍 Current page URL:", page.url)
            print("🔍 Page title:", page.title())

            # Step 2: Enter Kellogg email
            print("📧 Step 2: Entering Kellogg email...")
            try:
                # Try to find the specific email input field
                email_input = page.wait_for_selector("#email-address-identifier", timeout=10000)
                if not email_input:
                    # Fallback to other selectors if the specific ID isn't found
                    email_selectors = [
                        "input[type='email']",
                        "input[name='email']",
                        "input[placeholder*='email']",
                        "input[placeholder*='Email']",
                        "input[data-testid*='email']",
                        "input[id*='email']"
                    ]

                    for selector in email_selectors:
                        try:
                            email_input = page.wait_for_selector(selector, timeout=3000)
                            if email_input:
                                print(f"✅ Found email input with selector: {selector}")
                                break
                        except:
                            continue

                if not email_input:
                    print("❌ Could not find email input field")
                    # Take a screenshot for debugging
                    page.screenshot(path="handshake_debug.png")
                    return jobs

                print("✅ Found email input field")
                email_input.fill(KELLOGG_EMAIL or "")

                # Blur the input field to enable the Next button
                print("🖱️ Blurring email input to enable Next button...")
                # Use JavaScript to blur the element
                page.evaluate("document.getElementById('email-address-identifier').blur()")
                page.wait_for_timeout(1000)

                # Click Next button
                next_selectors = [
                    "button:has-text('Next')",
                    "input[type='submit']",
                    "button[type='submit']",
                    "button:has-text('Continue')",
                    "button:has-text('Sign in')"
                ]

                next_clicked = False
                for selector in next_selectors:
                    try:
                        next_button = page.locator(selector).first
                        if next_button.is_visible() and next_button.is_enabled():
                            next_button.click()
                            print(f"✅ Clicked next button with selector: {selector}")
                            next_clicked = True
                            break
                    except:
                        continue

                if not next_clicked:
                    print("❌ Could not find or click next button")
                    # Take a screenshot for debugging
                    page.screenshot(path="handshake_next_button_debug.png")
                    return jobs

                page.wait_for_timeout(3000)

                # Step 3: Select Northwestern University Student NetID Login
                print("🎓 Step 3: Selecting Northwestern University Student NetID Login...")
                netid_selectors = [
                    "button:has-text('Northwestern University Student NetID Login')",
                    "a:has-text('Northwestern University Student NetID Login')",
                    "button:has-text('Northwestern')",
                    "a:has-text('Northwestern')",
                    "[data-testid*='northwestern']"
                ]

                netid_clicked = False
                for selector in netid_selectors:
                    try:
                        netid_button = page.locator(selector).first
                        if netid_button.is_visible():
                            netid_button.click()
                            print(f"✅ Clicked Northwestern button with selector: {selector}")
                            netid_clicked = True
                            break
                    except:
                        continue

                if not netid_clicked:
                    print("❌ Could not find Northwestern University login button")
                    return jobs

                page.wait_for_timeout(3000)

                # Step 4: Login with NetID and Password
                print("🔑 Step 4: Logging in with NetID and Password...")
                try:
                    # Wait for page to load and check current URL
                    page.wait_for_timeout(3000)
                    print(f"🔍 Current URL after Northwestern click: {page.url}")
                    print(f"🔍 Page title: {page.title()}")

                    # Try different selectors for username field
                    username_selectors = [
                        "#txtUsername",
                        "input[name='username']",
                        "input[name='user']",
                        "input[type='text']",
                        "input[placeholder*='username']",
                        "input[placeholder*='Username']",
                        "input[id*='username']",
                        "input[id*='user']"
                    ]

                    username_input = None
                    for selector in username_selectors:
                        try:
                            username_input = page.wait_for_selector(selector, timeout=3000)
                            if username_input:
                                print(f"✅ Found username input with selector: {selector}")
                                break
                        except:
                            continue

                    if not username_input:
                        print("❌ Could not find username input field")
                        page.screenshot(path="handshake_netid_debug.png")
                        return jobs

                    # Try different selectors for password field
                    password_selectors = [
                        "#txtPassword",
                        "input[name='password']",
                        "input[type='password']",
                        "input[placeholder*='password']",
                        "input[placeholder*='Password']",
                        "input[id*='password']"
                    ]

                    password_input = None
                    for selector in password_selectors:
                        try:
                            password_input = page.wait_for_selector(selector, timeout=3000)
                            if password_input:
                                print(f"✅ Found password input with selector: {selector}")
                                break
                        except:
                            continue

                    if not password_input:
                        print("❌ Could not find password input field")
                        return jobs

                    # Fill in credentials
                    username_input.fill(NETID or "")
                    password_input.fill(PASSWORD or "")

                    # Try different selectors for login button
                    login_selectors = [
                        "#btnLogin",
                        "input[type='submit']",
                        "button[type='submit']",
                        "button:has-text('Login')",
                        "button:has-text('Sign in')",
                        "input[value*='Login']",
                        "input[value*='Sign in']"
                    ]

                    login_clicked = False
                    for selector in login_selectors:
                        try:
                            login_button = page.locator(selector).first
                            if login_button.is_visible():
                                login_button.click()
                                print(f"✅ Clicked login button with selector: {selector}")
                                login_clicked = True
                                break
                        except:
                            continue

                    if not login_clicked:
                        print("❌ Could not find login button")
                        return jobs

                    page.wait_for_timeout(5000)
                    print("✅ Successfully logged in with NetID")

                except Exception as e:
                    print(f"❌ Error during NetID login: {e}")
                    page.screenshot(path="handshake_netid_error.png")
                    return jobs

            except Exception as e:
                print(f"❌ Error during email entry: {e}")
                return jobs

            # Step 5: Navigate to job search page
            print("🔍 Step 5: Navigating to job search page...")
            job_search_url = "https://app.joinhandshake.com/job-search?query=product+manager+intern&pay%5BsalaryType%5D=1&jobType=3&jobRoleGroups=34&remoteWork=onsite&remoteWork=hybrid&locationFilter=%7B%22distance%22%3A%2250mi%22%2C%22label%22%3A%22San+Francisco%2C+CA%22%2C%22type%22%3A%22place%22%2C%22point%22%3A%2237.774929%2C-122.419415%22%2C%22text%22%3Anull%7D&locationFilter=%7B%22distance%22%3A%2250mi%22%2C%22label%22%3A%22New+York%2C+NY%22%2C%22type%22%3A%22place%22%2C%22point%22%3A%2240.712784%2C-74.005941%22%2C%22text%22%3Anull%7D&locationFilter=%7B%22distance%22%3A%2250mi%22%2C%22label%22%3A%22California%2C+United+States%22%2C%22type%22%3A%22region%22%2C%22point%22%3A%2237.07436%2C-119.699375%22%2C%22text%22%3A%22California%22%7D&locationFilter=%7B%22distance%22%3A%2250mi%22%2C%22label%22%3A%22Chicago%2C+Illinois%2C+United+States%22%2C%22type%22%3A%22place%22%2C%22point%22%3A%2241.881953%2C-87.632362%22%2C%22text%22%3A%22Chicago%22%7D&page=1&per_page=25"

            page.goto(job_search_url)
            page.wait_for_timeout(5000)

            # DEBUG: Inspect page structure
            debug_page_structure(page)

            # Step 6: Scroll to load all jobs
            print("📜 Step 6: Scrolling to load all jobs...")
            last_count = 0
            for i in range(10):  # Max 10 scrolls
                job_links = page.query_selector_all("a[href*='/job-search/']")
                count = len(job_links)
                print(f"🔽 Scroll {i+1}: found {count} job links")

                if count == last_count and i > 2:
                    print("✅ All jobs loaded")
                    break
                last_count = count

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            # Step 7: Scrape job data
            print("🎯 Step 7: Scraping job data...")
            job_links = page.query_selector_all("a[href*='/job-search/']")
            print(f"🔍 Final job count: {len(job_links)}")

            for i, job_link in enumerate(job_links):
                print(f"\n🔍 Processing job {i+1}:")

                job_info = extract_job_info(job_link, page)
                if not job_info:
                    continue

                title = job_info["title"]
                company = job_info["company"]
                location = job_info["location"]
                print(f"  📝 Title: {title}")
                print(f"  🏢 Company: {company}")
                print(f"  📍 Location: {location}")

                # Filter by keywords
                title_lower = title.lower()
                if ("product" in title_lower and
                    ("intern" in title_lower or "internship" in title_lower)):
                    jobs.append(job_info)
                    print(f"  ✅ Added to jobs list!")
                else:
                    print(f"  ⏭️ Skipped (doesn't match filter)")

        except Exception as e:
            print(f"❌ Error during scraping: {e}")

        finally:
            browser.close()

    return jobs


if __name__ == "__main__":
    results = login_and_scrape()
    print(f"\n🎯 FINAL RESULTS: {len(results)} jobs found")
    print(json.dumps(results, indent=2))
