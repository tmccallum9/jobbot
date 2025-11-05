import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from config_loader import get_config
import logging

# Load environment variables
load_dotenv()
NETID = os.getenv("KELLOGG_NETID") or os.getenv("UNIVERSITY_USERNAME")
PASSWORD = os.getenv("KELLOGG_PASS") or os.getenv("UNIVERSITY_PASSWORD")

logger = logging.getLogger(__name__)

assert NETID, "❌ NETID not found in .env"
assert PASSWORD, "❌ PASSWORD not found in .env"


def debug_page_structure(page):
    """Debug function to inspect the page structure"""
    logger.debug("🔍 DEBUGGING PAGE STRUCTURE:")

    # Check if table exists
    table = page.query_selector("table#jobPostingsContent")
    if table:
        logger.debug("✅ Found table#jobPostingsContent")
    else:
        logger.debug("❌ table#jobPostingsContent not found")

    # Check for different possible row selectors
    possible_selectors = [
        "tr.job-posting",
        "tr",
        "tbody tr",
        ".job-posting",
        "[class*='job']",
        "table tr"
    ]

    for selector in possible_selectors:
        rows = page.query_selector_all(selector)
        logger.debug(f"🔍 Selector '{selector}': {len(rows)} elements found")
        if len(rows) > 0:
            # Print first row's HTML structure
            first_row_html = rows[0].inner_html()
            logger.debug(f"   First row HTML: {first_row_html[:200]}...")

    # Check for title, company, location, and link elements in first few rows
    all_rows = page.query_selector_all("tr")
    logger.debug("🔍 Checking first 3 rows for all elements:")
    for i, row in enumerate(all_rows[:3]):
        logger.debug(f"Row {i+1}:")

        # Check all table cells
        cells = row.query_selector_all("td")
        logger.debug(f"  📊 Found {len(cells)} table cells")
        for j, cell in enumerate(cells):
            cell_text = cell.inner_text().strip()
            if cell_text:
                logger.debug(f"    Cell {j+1}: '{cell_text[:50]}...'")

        # Check for specific elements
        element_types = {
            "title": ["span.primary-item-text", "a.job-title", "span", "a",
                      "[class*='title']", "[class*='job']"],
            "company": ["[class*='company']", "[class*='employer']",
                        "span", "div", "td"],
            "location": ["[class*='location']", "[class*='city']",
                         "span", "div", "td"]
        }

        for element_type, selectors in element_types.items():
            logger.debug(f"  🔍 {element_type.upper()} candidates:")
            for selector in selectors:
                elements = row.query_selector_all(selector)
                if elements:
                    logger.debug(f"    {selector}: {len(elements)} found")
                    for k, el in enumerate(elements[:2]):  # Show first 2
                        text = el.inner_text().strip()
                        if text:
                            logger.debug(f"      [{k+1}] '{text[:50]}...'")


def extract_company_and_location(row, title):
    """Extract company and location from table row using intelligent analysis"""
    cells = row.query_selector_all("td")
    company = "Unknown"
    location = "N/A"

    if len(cells) < 2:
        return company, location

    # Analyze each cell to determine what it contains
    cell_data = []
    for i, cell in enumerate(cells):
        text = cell.inner_text().strip()
        if text and text != title:
            cell_data.append({
                'index': i,
                'text': text,
                'length': len(text),
                'has_commas': ',' in text,
                'has_http': 'http' in text.lower(),
                'is_likely_location': any(word in text.lower() for word in
                                          ['city', 'state', 'ca', 'ny', 'il',
                                           'tx', 'wa', 'ma', 'remote',
                                           'hybrid'])
            })

    # Sort by likelihood of being company vs location
    for cell in cell_data:
        if cell['has_http'] or cell['length'] > 100:
            continue  # Skip URLs and very long text

        # Company is usually shorter, no commas, not location-like
        if (not cell['has_commas'] and
                not cell['is_likely_location'] and
                cell['length'] < 50 and
                company == "Unknown"):
            company = cell['text']

        # Location often has commas, location keywords, or is in later columns
        elif (cell['has_commas'] or
                cell['is_likely_location'] or
                cell['index'] > 1) and location == "N/A":
            location = cell['text']

    return company, location


def scroll_to_load_all(page, row_selector="tr", pause=1500, max_scrolls=30):
    """Scroll until all lazy-loaded rows are visible or max_scrolls reached."""
    last_count = 0
    for i in range(max_scrolls):
        # Count current rows
        rows = page.query_selector_all(row_selector)
        count = len(rows)
        logger.debug(f"Scroll {i+1}: found {count} rows")

        # If no new rows appear, stop
        if count == last_count and i > 2:  # Allow at least 3 scrolls
            logger.debug("✅ All rows loaded")
            break
        last_count = count

        # Scroll to bottom and wait
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(pause)

    return page.query_selector_all(row_selector)


def login_and_scrape():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Step 1: Navigate to 12twenty SSO
        page.goto("https://12twenty-sso.kellogg.northwestern.edu/")
        page.locator("p:has-text('Student Login')").click()

        # Step 2: Login
        page.wait_for_selector("#txtUsername", timeout=15000)
        page.fill("#txtUsername", NETID or "")
        page.fill("#txtPassword", PASSWORD or "")
        page.click("#btnLogin")

        # Step 3: Navigate to job postings
        page.goto("https://kellogg-northwestern.12twenty.com/jobPostings")
        page.wait_for_selector("table#jobPostingsContent", timeout=20000)
        logger.info("📄 Job postings table loaded successfully")

        # DEBUG: Inspect page structure (only runs if log level is DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            debug_page_structure(page)

        # Wait a bit more for dynamic content
        page.wait_for_timeout(3000)

        # Step 4: Scroll to load all rows (try different selectors)
        possible_row_selectors = ["tr", "tbody tr", ".job-posting", "table tr"]
        rows = []

        for selector in possible_row_selectors:
            rows = scroll_to_load_all(page, selector)
            if len(rows) > 0:
                logger.info(f"✅ Using selector '{selector}' - found {len(rows)} rows")
                break

        if not rows:
            logger.error("❌ No rows found with any selector!")
            browser.close()
            return jobs

        logger.info(f"Final row count: {len(rows)}")

        # Step 5: Scrape job data with multiple selector attempts
        for i, row in enumerate(rows):
            logger.debug(f"🔍 Processing row {i+1}:")

            # Try multiple selectors for title and link
            title_selectors = [
                "span.primary-item-text",
                "a.job-title",
                "span",
                "a",
                "[class*='title']",
                "td:first-child span",
                "td:first-child a"
            ]

            title_el = None
            link_el = None

            for selector in title_selectors:
                title_el = row.query_selector(selector)
                if title_el and title_el.inner_text().strip():
                    title_text = title_el.inner_text().strip()[:50]
                    logger.debug(f"  ✅ Found title with selector '{selector}': {title_text}...")
                    break

            # Look for link elements
            link_selectors = [
                "a.job-title",
                "a",
                "td a"
            ]

            for selector in link_selectors:
                link_el = row.query_selector(selector)
                if link_el and link_el.get_attribute("href"):
                    logger.debug(f"  ✅ Found link with selector '{selector}'")
                    break

            if not title_el:
                logger.debug(f"  ❌ Skipping row {i+1} - missing title")
                continue

            title = title_el.inner_text().strip()
            href = link_el.get_attribute("href") if link_el else None

            # Extract company and location using intelligent analysis
            company, location = extract_company_and_location(row, title)

            logger.debug(f"  📝 Title: {title}")
            logger.debug(f"  🏢 Company: {company}")
            logger.debug(f"  📍 Location: {location}")
            if href:
                logger.debug(f"  🔗 Link: {href}")
            else:
                logger.debug(f"  ⚠️ No link found for this job")

            # Filter by keywords using config
            config = get_config()
            if config.matches_title_filter(title):
                job_data = {
                    "title": title,
                    "company": company,
                    "location": location
                }
                # Only add URL if href is available
                if href:
                    job_data["url"] = f"https://kellogg-northwestern.12twenty.com{href}"
                else:
                    job_data["url"] = ""

                jobs.append(job_data)
                logger.info(f"  ✅ Added to jobs list: {title}")
            else:
                logger.debug("  ⏭️ Skipped (doesn't match filter)")

        browser.close()
    return jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = login_and_scrape()
    logger.info(f"🎯 FINAL RESULTS: {len(results)} jobs found")
    logger.info(json.dumps(results, indent=2))
