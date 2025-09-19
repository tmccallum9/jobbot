import os
import urllib
from notion_client import Client
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

load_dotenv()

# Expect NOTION_API_KEY to be set (aligns with README and deployment docs)
NOTION_API_KEY = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    raise RuntimeError("NOTION_API_KEY (or NOTION_TOKEN) is not set in environment")
if not NOTION_DATABASE_ID:
    raise RuntimeError("NOTION_DATABASE_ID is not set in environment")

notion = Client(auth=NOTION_API_KEY)
db_id = NOTION_DATABASE_ID


def normalize_url(u: str) -> str:
    parsed = urlparse(u.strip())
    # Remove default ports, trailing slashes, lowercase scheme/host
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower().rstrip(':80').rstrip(':443'),
        path=parsed.path.rstrip('/')
    )
    return urlunparse(normalized)


def get_jobs_from_notion(title: str, company: str, url: str):
    url = normalize_url(url)  # normalize before querying
    try:
        response = notion.databases.query(
            database_id=db_id,
            filter={
                "and": [
                    {
                        "property": "Job Title",
                        "title": {"equals": title}
                    },
                    {
                        "property": "Company",
                        "rich_text": {"equals": company}
                    },
                    {
                        "property": "Application URL",
                        "url": {"equals": url}
                    }
                ]
            }
        )

        for result in response.get("results", []):
            notion_url = result.get("properties", {}).get("Application URL", {}).get("url", "")
            if normalize_url(notion_url) == url:
                return True
        return False
    except Exception as e:
        print(f"❌ Error querying Notion for '{title}' at '{company}': {e}")
        return False


def push_job_to_notion(job):
    try:
        normalized_url = normalize_url(job.get("url", ""))
        notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "Job Title": {"title": [{"text": {"content": job.get("title", "")}}]},
                "Company": {"rich_text": [{"text": {"content": job.get("company", "")}}]},
                "Location": {"rich_text": [{"text": {"content": job.get("location", "")}}]},
                "Application URL": {"url": normalized_url}
            }
        )
    except Exception as e:
        print(f"❌ Error creating Notion page for '{job.get('title','')}' at '{job.get('company','')}': {e}")
        raise
