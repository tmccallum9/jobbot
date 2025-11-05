import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config_loader import get_config
import logging

logger = logging.getLogger(__name__)


def scrape_linkedin_pm_internships():
    config = get_config()
    url = config.get_scraper_url("linkedin")

    if not url:
        logger.warning("⚠️ LinkedIn scraper URL not configured, using default")
        url = (
            "https://www.linkedin.com/jobs/search/?currentJobId=4279913253&distance=25"
            "&f_E=1%2C3%2C4&f_F=prdm%2Cmrkt%2Cit%2Cmgmt%2Canls"
            "&f_JT=I"
            "&f_PP=106233382%2C102571732%2C104116203%2C106504367%2C100075706%2C102277331%2C102250832%2C103112676"
            "&f_T=27%2C270%2C9572%2C2995"
            "&f_TPR=r2592000"
            "&f_WT=1%2C3"
            "&geoId=103644278"
            "&keywords=Product%20Manager%20Intern"
            "&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
        )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []

    listings = soup.select("ul.jobs-search__results-list li")

    logger.info(f"🔍 Found {len(listings)} LinkedIn job cards")

    for card in listings:
        try:
            title_tag = card.select_one("h3")
            company_tag = card.select_one("h4")
            location_tag = card.select_one(".job-search-card__location")
            link_tag = card.select_one("a")

            title = title_tag.text.strip() if title_tag else "N/A"
            company = company_tag.text.strip() if company_tag else "N/A"
            location = location_tag.text.strip() if location_tag else "N/A"
            job_url = urljoin("https://www.linkedin.com", link_tag["href"]) if link_tag and link_tag.has_attr("href") else ""

            # Use config to match title filter instead of hardcoded check
            if config.matches_title_filter(title):
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url
                })

                logger.info(f"✅ {title} at {company} — {location}")
                logger.info(f"🔗 {job_url}")

        except Exception as e:
            logger.error(f"❌ Error parsing LinkedIn job: {e}")

    return jobs
