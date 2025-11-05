from contextlib import asynccontextmanager
from fastapi import FastAPI
from builtin_scraper import scrape_builtin_pm_internships
from linkedin_scraper import scrape_linkedin_pm_internships
from CMS_scraper import login_and_scrape as scrape_cms_jobs
from handshake_scraper import login_and_scrape as scrape_handshake_jobs
from notion_api import push_job_to_notion, get_jobs_from_notion
from apscheduler.triggers.cron import CronTrigger
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from config_loader import get_config
import os


# Logging setup
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# Scheduler setup
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan manager"""
    # Startup
    logger.info("🚀 Starting scheduler...")
    scheduler.start()
    yield
    # Shutdown
    logger.info("🛑 Shutting down scheduler...")
    scheduler.shutdown()


app = FastAPI(
    title="JobBot",
    description="Automated job scraping and Notion integration",
    version="2.0.0",
    lifespan=lifespan
)


def run_scraper_job():
    logger.info("🚀 Running job scraper...")

    # Initialize job lists
    builtin_jobs = []
    linkedin_jobs = []
    cms_jobs = []
    handshake_jobs = []

    try:
        # Run scrapers only if enabled in config
        if config.is_scraper_enabled("builtin"):
            logger.info("🔍 Running BuiltIn scraper...")
            builtin_jobs = scrape_builtin_pm_internships()
        else:
            logger.info("⏭️ BuiltIn scraper disabled in config")

        if config.is_scraper_enabled("linkedin"):
            logger.info("🔍 Running LinkedIn scraper...")
            linkedin_jobs = scrape_linkedin_pm_internships()
        else:
            logger.info("⏭️ LinkedIn scraper disabled in config")

        if config.is_scraper_enabled("cms"):
            logger.info("🔍 Running CMS scraper...")
            cms_jobs = scrape_cms_jobs()
        else:
            logger.info("⏭️ CMS scraper disabled in config")

        if config.is_scraper_enabled("handshake"):
            logger.info("🔍 Running Handshake scraper...")
            handshake_jobs = scrape_handshake_jobs()
        else:
            logger.info("⏭️ Handshake scraper disabled in config")

    except Exception as e:
        logger.exception(f"❌ Top-level scrape failure: {e}")
        return {
            "error": "scrape_failed",
            "message": str(e)
        }

    all_jobs = (builtin_jobs or []) + (linkedin_jobs or []) + (cms_jobs or []) + (handshake_jobs or [])

    logger.info(f"📊 Scraped {len(builtin_jobs or [])} jobs from BuiltIn.")
    logger.info(f"📊 Scraped {len(linkedin_jobs or [])} jobs from LinkedIn.")
    logger.info(f"📊 Scraped {len(cms_jobs or [])} jobs from CMS (12twenty).")
    logger.info(f"📊 Scraped {len(handshake_jobs or [])} jobs from Handshake.")
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

            if get_jobs_from_notion(title, company, url):
                logger.info(f"🟡 Skipping duplicate: {title} at {company}")
                continue

            logger.info(f"🆕 Adding job: {title} at {company} ({location})")
            if url:
                logger.info(f"→ URL: {url}")
            else:
                logger.warning(f"⚠️ No URL available for this job")
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
    CronTrigger.from_crontab(config.get_cron_schedule(), timezone=config.get_timezone()),
    id="daily_scraper_job",
    replace_existing=True
)


@app.on_event("startup")
def startup_scheduler():
    logger.info("🚀 Starting scheduler...")
    scheduler.start()


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "scrapers": {
            "builtin": config.is_scraper_enabled("builtin"),
            "linkedin": config.is_scraper_enabled("linkedin"),
            "cms": config.is_scraper_enabled("cms"),
            "handshake": config.is_scraper_enabled("handshake")
        },
        "scheduler": {
            "cron": config.get_cron_schedule(),
            "timezone": config.get_timezone()
        }
    }


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
