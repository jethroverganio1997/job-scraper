"""Job scraper package providing scraping utilities."""

from .linkedin_scraper import LinkedInScraper
from .scraper import JobListing, JobScraper

__all__ = ["JobScraper", "JobListing", "LinkedInScraper"]
