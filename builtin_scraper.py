import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_builtin_pm_internships():
    url = "https://builtin.com/jobs/hybrid/office/product?search=Product+Manager%2C+Intern&country=USA&allLocations=true"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    listings = soup.select('div[data-id="job-card"]')
    print(f"🔍 Found {len(listings)} job cards\n")

    for card in listings:
        try:
            title_tag = card.select_one('a[data-id="job-card-title"]')
            if not title_tag or not title_tag.has_attr('href'):
                print("⚠️ Missing job title or URL, skipping.")
                continue

            title = title_tag.text.strip()
            href = title_tag['href']
            job_url = urljoin("https://builtin.com", href)

            company_tag = card.select_one('a[data-id="company-title"] span')
            company = company_tag.text.strip() if company_tag else "Unknown"

            tooltip = card.select_one('span[data-bs-toggle="tooltip"]')
            if tooltip:
                tooltip_html = tooltip.get('data-bs-title', '')
                locations_soup = BeautifulSoup(tooltip_html, 'html.parser')
                location = ', '.join([div.text for div in locations_soup.select('div')])
            else:
                location = "N/A"

            job = {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url
            }

            jobs.append(job)

            print(f"✅ {title} at {company}")
            print(f"📍 {location}")
            print(f"🔗 {job_url}\n")

        except Exception as e:
            print("❌ Error parsing job:", e)

    return jobs
