import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config_loader import get_config
import logging

logger = logging.getLogger(__name__)

def scrape_builtin_pm_internships():
    config = get_config()
    url = config.get_scraper_url("builtin")

    if not url:
        logger.warning("⚠️ BuiltIn scraper URL not configured, using default")
        url = "https://builtin.com/jobs/hybrid/office/product?search=Product+Manager%2C+Intern&country=USA&allLocations=true"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    listings = soup.select('div[data-id="job-card"]')
    logger.info(f"🔍 Found {len(listings)} job cards")

    for card in listings:
        try:
            title_tag = card.select_one('a[data-id="job-card-title"]')
            if not title_tag:
                logger.warning("⚠️ Missing job title, skipping.")
                continue

            title = title_tag.text.strip()
            
            # Try to get URL, but don't skip if missing
            job_url = ""
            if title_tag.has_attr('href'):
                href = title_tag['href']
                job_url = urljoin("https://builtin.com", href)
            else:
                logger.warning("⚠️ No URL found for this job")

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

            logger.info(f"✅ {title} at {company}")
            logger.info(f"📍 {location}")
            if job_url:
                logger.info(f"🔗 {job_url}")
            else:
                logger.warning(f"⚠️ No URL available")

        except Exception as e:
            logger.error(f"❌ Error parsing job: {e}")

    return jobs
