import os
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()
NETID = os.getenv("KELLOGG_NETID")
PASSWORD = os.getenv("KELLOGG_PASS")

assert NETID, "❌ NETID not found in .env"
assert PASSWORD, "❌ PASSWORD not found in .env"


def debug_page_structure(page):
    """Debug function to inspect the page structure"""
    print("🔍 DEBUGGING PAGE STRUCTURE:")

    # Check if table exists
    table = page.query_selector("table#jobPostingsContent")
    if table:
        print("✅ Found table#jobPostingsContent")
    else:
        print("❌ table#jobPostingsContent not found")

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
        print(f"🔍 Selector '{selector}': {len(rows)} elements found")
        if len(rows) > 0:
            # Print first row's HTML structure
            first_row_html = rows[0].inner_html()
            print(f"   First row HTML: {first_row_html[:200]}...")

    # Check for title, company, location, and link elements in first few rows
    all_rows = page.query_selector_all("tr")
    print("\n🔍 Checking first 3 rows for all elements:")
    for i, row in enumerate(all_rows[:3]):
        print(f"\nRow {i+1}:")

        # Check all table cells
        cells = row.query_selector_all("td")
        print(f"  📊 Found {len(cells)} table cells")
        for j, cell in enumerate(cells):
            cell_text = cell.inner_text().strip()
            if cell_text:
                print(f"    Cell {j+1}: '{cell_text[:50]}...'")

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
            print(f"  🔍 {element_type.upper()} candidates:")
            for selector in selectors:
                elements = row.query_selector_all(selector)
                if elements:
                    print(f"    {selector}: {len(elements)} found")
                    for k, el in enumerate(elements[:2]):  # Show first 2
                        text = el.inner_text().strip()
                        if text:
                            print(f"      [{k+1}] '{text[:50]}...'")


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
        print(f" Scroll {i+1}: found {count} rows")

        # If no new rows appear, stop
        if count == last_count and i > 2:  # Allow at least 3 scrolls
            print("✅ All rows loaded")
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
        print("📄 Job postings table loaded successfully")

        # DEBUG: Inspect page structure
        debug_page_structure(page)

        # Wait a bit more for dynamic content
        page.wait_for_timeout(3000)

        # Step 4: Scroll to load all rows (try different selectors)
        possible_row_selectors = ["tr", "tbody tr", ".job-posting", "table tr"]
        rows = []

        for selector in possible_row_selectors:
            rows = scroll_to_load_all(page, selector)
            if len(rows) > 0:
                print(f"✅ Using selector '{selector}' - found {len(rows)} rows")
                break

        if not rows:
            print("❌ No rows found with any selector!")
            browser.close()
            return jobs

        print(f" Final row count: {len(rows)}")

        # Step 5: Scrape job data with multiple selector attempts
        for i, row in enumerate(rows):
            print(f"\n🔍 Processing row {i+1}:")

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
                    print(f"  ✅ Found title with selector '{selector}': "
                          f"{title_text}...")
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
                    print(f"  ✅ Found link with selector '{selector}'")
                    break

            if not title_el or not link_el:
                print(f"  ❌ Skipping row {i+1} - missing title or link")
                continue

            title = title_el.inner_text().strip()
            href = link_el.get_attribute("href")

            # Extract company and location using intelligent analysis
            company, location = extract_company_and_location(row, title)

            print(f"  📝 Title: {title}")
            print(f"  🏢 Company: {company}")
            print(f"  📍 Location: {location}")
            print(f"  🔗 Link: {href}")

            # Filter by keywords
            title_lower = title.lower()
            if ("product" in title_lower and
                    ("intern" in title_lower or "internship" in title_lower)):
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": f"https://kellogg-northwestern.12twenty.com{href}"
                })
                print("  ✅ Added to jobs list!")
            else:
                print("  ⏭️ Skipped (doesn't match filter)")

        browser.close()
    return jobs


if __name__ == "__main__":
    results = login_and_scrape()
    print(f"\n🎯 FINAL RESULTS: {len(results)} jobs found")
    print(json.dumps(results, indent=2))
