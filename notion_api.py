import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
db_id = os.getenv("NOTION_DATABASE_ID")


def get_jobs_from_notion(title: str, company: str):
    try:
        response = notion.databases.query(
            **{
                "database_id": db_id,
                "filter": {
                    "and": [
                        {
                            "property": "Job Title",
                            "title": {
                                "equals": title
                            }
                        },
                        {
                            "property": "Company",
                            "rich_text": {
                                "equals": company
                            }
                        }
                    ]
                }
            }
        )
        return len(response["results"]) > 0
    except Exception as e:
        print(f"❌ Error querying Notion for '{title}' at '{company}': {e}")
        return False


def push_job_to_notion(job):
    notion.pages.create(
        parent={"database_id": db_id},
        properties={
            "Job Title": {"title": [{"text": {"content": job["title"]}}]},
            "Company": {"rich_text": [{"text": {"content": job["company"]}}]},
            "Location": {"rich_text": [{"text": {"content": job["location"]}}]},
            "Application URL": {"url": job["url"]}
        }
    )
