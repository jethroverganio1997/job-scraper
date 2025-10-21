"""Seek job scraper powered by Crawl4AI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from dotenv import load_dotenv


@dataclass
class JobListing:
    """Representation of a single job card scraped from Seek."""

    title: str
    company: Optional[str]
    location: Optional[str]
    salary: Optional[str]
    listing_date: Optional[str]
    job_url: Optional[str]
    summary: Optional[str] = None
    job_id: Optional[str] = None
    source: str = "Seek"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the job listing into a JSON-friendly dictionary."""

        return asdict(self)


class JobScraper:
    """Scrape Seek job listings using Crawl4AI."""

    SEEK_ROOT_URL = "https://www.seek.com.au"
    SEEK_SEARCH_URL = f"{SEEK_ROOT_URL}/jobs"

    def __init__(
        self,
        *,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        max_jobs: Optional[int] = None,
        max_pages: Optional[int] = None,
        date_filter: Optional[str] = None,
    ) -> None:
        load_dotenv()

        self.keywords = (keywords or os.getenv("SEEK_KEYWORDS", "software engineer")).strip()
        self.location = (location or os.getenv("SEEK_LOCATION", "Australia")).strip()
        self.max_jobs = self._parse_int(max_jobs or os.getenv("SEEK_MAX_JOBS"), default=20)
        self.max_pages = self._parse_int(max_pages or os.getenv("SEEK_MAX_PAGES"), default=1)
        self.date_filter = str(date_filter or os.getenv("SEEK_DATE_FILTER", "")).strip()

        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.logger.debug(
            "Initialized JobScraper with keywords=%s, location=%s, max_jobs=%s, max_pages=%s, date_filter=%s",
            self.keywords,
            self.location,
            self.max_jobs,
            self.max_pages,
            self.date_filter,
        )

    @staticmethod
    def _parse_int(value: Optional[Any], *, default: int) -> int:
        """Parse an integer value with a fallback default."""

        if value is None or value == "":
            return default
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    def build_search_url(self, page: int = 1) -> str:
        """Construct the Seek search URL for a specific page."""

        params: Dict[str, Any] = {
            "keywords": self.keywords,
            "where": self.location,
        }
        if page > 1:
            params["page"] = page
        if self.date_filter:
            params["daterange"] = self.date_filter
        query = urlencode(params)
        url = f"{self.SEEK_SEARCH_URL}?{query}"
        self.logger.debug("Constructed search URL for page %s: %s", page, url)
        return url

    def _create_crawler_config(self) -> CrawlerRunConfig:
        """Create the Crawl4AI configuration used for Seek pages."""

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            parser_type="lxml",
            verbose=False,
        )

    async def scrape_jobs_async(self) -> List[JobListing]:
        """Asynchronously scrape Seek job listings based on the configured parameters."""

        results: List[JobListing] = []
        crawler_config = self._create_crawler_config()

        try:
            async with AsyncWebCrawler() as crawler:
                for page in range(1, self.max_pages + 1):
                    if len(results) >= self.max_jobs:
                        break

                    search_url = self.build_search_url(page)
                    self.logger.info("Crawling %s", search_url)

                    crawl_result = await crawler.arun(url=search_url, config=crawler_config)
                    if not getattr(crawl_result, "success", False):
                        self.logger.warning("Failed to fetch page %s (%s)", page, search_url)
                        continue

                    page_jobs = self.parse_job_cards(crawl_result.html)
                    self.logger.info("Parsed %s jobs from page %s", len(page_jobs), page)

                    for job in page_jobs:
                        results.append(job)
                        if len(results) >= self.max_jobs:
                            break
        except Exception as exc:  # pragma: no cover - relies on runtime dependencies
            self.logger.error("Failed to crawl Seek: %s", exc)
            raise

        return results[: self.max_jobs]

    def scrape_jobs(self) -> List[Dict[str, Any]]:
        """Synchronously scrape jobs and return dictionaries for each listing."""

        listings = self._run_async(self.scrape_jobs_async())
        return [listing.to_dict() for listing in listings]

    def _run_async(self, coro: Any) -> Any:
        """Execute an async coroutine, handling already-running event loops."""

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError(
                "scrape_jobs cannot be called while an event loop is running. "
                "Use scrape_jobs_async() instead."
            )

        return asyncio.run(coro)

    def parse_job_cards(self, html: str) -> List[JobListing]:
        """Parse Seek HTML and extract job listings."""

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        cards: List[Any] = []
        selectors = [
            '[data-automation="normalJob"]',
            '[data-automation="premiumJob"]',
            '[data-automation="job-card"]',
        ]
        for selector in selectors:
            for card in soup.select(selector):
                if card not in cards:
                    cards.append(card)

        if not cards:
            # Fallback to generic article tags if data-automation markers change.
            cards = soup.find_all("article")

        job_listings: List[JobListing] = []
        for card in cards:
            job = self._parse_job_card(card)
            if job:
                job_listings.append(job)

        return job_listings

    def _parse_job_card(self, card: Any) -> Optional[JobListing]:
        """Convert a job card element into a :class:`JobListing`."""

        title = self._extract_text(card, ["jobTitle", "job-title"])
        if not title:
            return None

        company = self._extract_text(card, ["jobCompany", "job-company"])
        location = self._extract_text(card, ["jobLocation", "job-location"])
        salary = self._extract_text(card, ["jobSalary", "job-salary"])
        listing_date = self._extract_text(card, ["jobListingDate", "jobCardDate", "listing-date"])
        summary = self._extract_text(card, ["jobShortDescription", "job-short-description"])
        job_url = self._extract_job_url(card)
        job_id = self._extract_job_id(card)

        return JobListing(
            title=title,
            company=company,
            location=location,
            salary=salary,
            listing_date=listing_date,
            job_url=job_url,
            summary=summary,
            job_id=job_id,
        )

    def _extract_text(self, card: Any, automation_keys: Iterable[str]) -> Optional[str]:
        """Retrieve text content for a series of `data-automation` keys."""

        for key in automation_keys:
            element = card.find(attrs={"data-automation": key})
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        return None

    def _extract_job_url(self, card: Any) -> Optional[str]:
        """Extract the job posting URL from the card."""

        link = card.find("a", attrs={"data-automation": "jobTitle"})
        if not link:
            link = card.find("a", href=True)
        if not link:
            return None

        href = link.get("href")
        if not href:
            return None
        return urljoin(self.SEEK_ROOT_URL, href)

    @staticmethod
    def _extract_job_id(card: Any) -> Optional[str]:
        """Read the job identifier from known attributes."""

        for attribute in ("data-job-id", "data-search-sol-job-id", "data-job-id-hash"):
            value = card.get(attribute)
            if value:
                return str(value)
        return None

    def save_results(self, jobs: Iterable[JobListing | Dict[str, Any]], output_path: os.PathLike[str] | str) -> Path:
        """Persist scraped jobs to disk in JSON format."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        serializable: List[Dict[str, Any]] = []
        for job in jobs:
            if isinstance(job, JobListing):
                serializable.append(job.to_dict())
            elif isinstance(job, dict):
                serializable.append(job)
            else:
                raise TypeError(f"Unsupported job data type: {type(job)!r}")

        path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Saved %s job(s) to %s", len(serializable), path)
        return path
