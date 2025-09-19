from fastapi import FastAPI
from builtin_scraper import scrape_builtin_pm_internships
from linkedin_scraper import scrape_linkedin_pm_internships
from CMS_scraper import login_and_scrape as scrape_cms_jobs
from handshake_scraper import login_and_scrape as scrape_handshake_jobs
from notion_api import push_job_to_notion, get_jobs_from_notion
from apscheduler.triggers.cron import CronTrigger
import logging
from apscheduler.schedulers.background import BackgroundScheduler


# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

scheduler = BackgroundScheduler()


def run_scraper_job():
    logger.info("🚀 Running job scraper...")
    try:
        builtin_jobs = scrape_builtin_pm_internships()
        linkedin_jobs = scrape_linkedin_pm_internships()
        cms_jobs = scrape_cms_jobs()
        handshake_jobs = scrape_handshake_jobs()
    except Exception as e:
        logger.exception(f"❌ Top-level scrape failure: {e}")
        return {
            "error": "scrape_failed",
            "message": str(e)
        }

    all_jobs = (builtin_jobs or []) + (linkedin_jobs or []) + (cms_jobs or []) + (handshake_jobs or [])

    logger.info(f"📊 Scraped {len(builtin_jobs)} jobs from BuiltIn.")
    logger.info(f"📊 Scraped {len(linkedin_jobs)} jobs from LinkedIn.")
    logger.info(f"📊 Scraped {len(cms_jobs)} jobs from CMS (12twenty).")
    logger.info(f"📊 Scraped {len(handshake_jobs)} jobs from Handshake.")
    logger.info(f"🔢 Total jobs scraped: {len(all_jobs)}")

    added = 0
    for job in all_jobs:
        try:
            title = job.get("title", "")
            company = job.get("company", "")
            location = job.get("location", "")
            url = job.get("url", "")

            if not title or not company:
                logger.warning(f"⚠️ Skipping job with missing fields: title='{title}' company='{company}' url='{url}'")
                continue

            if get_jobs_from_notion(title, company):
                logger.info(f"🟡 Skipping duplicate: {title} at {company}")
                continue

            logger.info(f"🆕 Adding job: {title} at {company} ({location})")
            logger.info(f"→ URL: {url}")
            push_job_to_notion(job)
            added += 1

        except Exception as e:
            logger.exception(f"❌ Failed to add job '{job}': {e}")

    logger.info(f"✅ Finished run. Total new jobs added to Notion: {added}")

    return {
        "builtin_jobs": len(builtin_jobs),
        "linkedin_jobs": len(linkedin_jobs),
        "cms_jobs": len(cms_jobs),
        "handshake_jobs": len(handshake_jobs),
        "total_scraped": len(all_jobs),
        "total_added": added
    }


scheduler.add_job(
    run_scraper_job,
    CronTrigger.from_crontab("0 9 * * *", timezone="America/New_York"),
    id="daily_scraper_job",
    replace_existing=True
)


@app.on_event("startup")
def startup_scheduler():
    logger.info("🚀 Starting scheduler...")
    scheduler.start()


@app.get("/run-scraper")
def run_scraper_on_demand():
    logger.info("🚀 Received request to run scraper on demand.")
    try:
        results = run_scraper_job()
        return {
            "status": "ok",
            "sources": results
        }
    except Exception as e:
        logger.exception(f"❌ /run-scraper failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    run_scraper_job()
