"""
Configuration loader for JobBot
Loads and validates configuration from config.yaml
"""
import os
import yaml
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for JobBot"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"⚠️ Warning: {self.config_path} not found. Using default configuration.")
            return self._default_config()
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parsing {self.config_path}: {e}")
            logger.warning("⚠️ Using default configuration.")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file is missing"""
        return {
            "job_search": {
                "title_keywords": [
                    {"keywords": ["product", "intern"]}
                ],
                "locations": [
                    "San Francisco, CA",
                    "New York, NY",
                    "Chicago, IL"
                ],
                "remote_preferences": ["onsite", "hybrid"]
            },
            "scrapers": {
                "builtin": {"enabled": True},
                "linkedin": {"enabled": True},
                "cms": {"enabled": True},
                "handshake": {"enabled": True}
            },
            "notion": {
                "properties": {
                    "title": "Job Title",
                    "company": "Company",
                    "location": "Location",
                    "url": "Application URL",
                    "date_added": "Date Added"
                }
            },
            "scheduler": {
                "cron": "0 9 * * *",
                "timezone": "America/New_York"
            }
        }

    # Job Search Configuration
    def get_title_keywords(self) -> List[Dict[str, List[str]]]:
        """Get title keyword groups for filtering"""
        return self._config.get("job_search", {}).get("title_keywords", [{"keywords": ["product", "intern"]}])

    def matches_title_filter(self, title: str) -> bool:
        """
        Check if a job title matches any of the keyword groups
        Returns True if at least one keyword group matches
        """
        title_lower = title.lower()
        keyword_groups = self.get_title_keywords()

        for group in keyword_groups:
            keywords = group.get("keywords", [])
            # All keywords in the group must be present (AND logic)
            if all(keyword.lower() in title_lower for keyword in keywords):
                return True

        return False

    def get_locations(self) -> List[str]:
        """Get configured locations"""
        return self._config.get("job_search", {}).get("locations", [])

    def get_remote_preferences(self) -> List[str]:
        """Get remote work preferences"""
        return self._config.get("job_search", {}).get("remote_preferences", ["onsite", "hybrid"])

    # Scraper Configuration
    def is_scraper_enabled(self, scraper_name: str) -> bool:
        """Check if a scraper is enabled"""
        return self._config.get("scrapers", {}).get(scraper_name, {}).get("enabled", False)

    def get_scraper_url(self, scraper_name: str) -> str:
        """Get the search URL for a scraper"""
        return self._config.get("scrapers", {}).get(scraper_name, {}).get("search_url", "")

    # Notion Configuration
    def get_notion_property(self, property_key: str) -> str:
        """Get Notion property name by key (title, company, location, url, date_added)"""
        return self._config.get("notion", {}).get("properties", {}).get(property_key, property_key.title())

    # Scheduler Configuration
    def get_cron_schedule(self) -> str:
        """Get cron schedule expression"""
        return self._config.get("scheduler", {}).get("cron", "0 9 * * *")

    def get_timezone(self) -> str:
        """Get scheduler timezone"""
        return self._config.get("scheduler", {}).get("timezone", "America/New_York")


# Global configuration instance
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Convenience functions
def matches_job_filter(title: str) -> bool:
    """Check if a job title matches the configured filters"""
    return get_config().matches_title_filter(title)

def is_scraper_enabled(scraper_name: str) -> bool:
    """Check if a scraper is enabled"""
    return get_config().is_scraper_enabled(scraper_name)
