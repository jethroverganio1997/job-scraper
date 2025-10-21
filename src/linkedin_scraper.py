"""LinkedIn job scraper powered by Crawl4AI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, NavigableString, Tag
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from dotenv import load_dotenv

from .scraper import JobListing


@dataclass
class LinkedInSearchConfig:
    """Configuration values for LinkedIn scraping."""

    keywords: str
    location: str
    max_jobs: int
    max_pages: int
    time_filter_seconds: Optional[int]


class LinkedInScraper:
    """Scrape LinkedIn job listings using Crawl4AI."""

    ROOT_URL = "https://www.linkedin.com"
    SEARCH_PATH = "/jobs/search"
    JOBS_PER_PAGE = 25

    def __init__(
        self,
        *,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        max_jobs: Optional[int] = None,
        max_pages: Optional[int] = None,
        time_filter_seconds: Optional[int] = None,
    ) -> None:
        load_dotenv()

        self.config = LinkedInSearchConfig(
            keywords=(keywords or os.getenv("LINKEDIN_KEYWORDS", "software engineer")).strip(),
            location=(location or os.getenv("LINKEDIN_LOCATION", "United States")).strip(),
            max_jobs=self._parse_int(max_jobs or os.getenv("LINKEDIN_MAX_JOBS"), default=20),
            max_pages=self._parse_int(max_pages or os.getenv("LINKEDIN_MAX_PAGES"), default=1),
            time_filter_seconds=self._parse_time_filter(
                time_filter_seconds or os.getenv("LINKEDIN_TIME_FILTER", "86400")
            ),
        )

        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger = logging.getLogger(logger_name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self.logger.debug(
            "Initialized LinkedInScraper with keywords=%s, location=%s, max_jobs=%s, max_pages=%s, time_filter_seconds=%s",
            self.config.keywords,
            self.config.location,
            self.config.max_jobs,
            self.config.max_pages,
            self.config.time_filter_seconds,
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

    @staticmethod
    def _parse_time_filter(value: Optional[Any]) -> Optional[int]:
        """Parse time filter seconds or return ``None`` for no filter."""

        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            seconds = int(text)
        except ValueError:
            return None
        return max(seconds, 0)

    def build_search_url(self, page: int = 1) -> str:
        """Construct the LinkedIn search URL for a specific page."""

        params: Dict[str, Any] = {
            "keywords": self.config.keywords,
            "location": self.config.location,
            "refresh": "true",
        }
        if page > 1:
            params["start"] = (page - 1) * self.JOBS_PER_PAGE
        if self.config.time_filter_seconds and self.config.time_filter_seconds > 0:
            params["f_TPR"] = f"r{self.config.time_filter_seconds}"
        query = urlencode(params)
        url = f"{self.ROOT_URL}{self.SEARCH_PATH}?{query}"
        self.logger.debug("Constructed LinkedIn search URL for page %s: %s", page, url)
        return url

    def _create_crawler_config(self) -> CrawlerRunConfig:
        """Create the Crawl4AI configuration for search pages."""

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            parser_type="lxml",
            extra_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            viewport={"width": 1280, "height": 720},
            verbose=False,
        )

    def _create_detail_crawler_config(self) -> CrawlerRunConfig:
        """Create the Crawl4AI configuration for job detail pages."""

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="domcontentloaded",
            parser_type="lxml",
            extra_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            viewport={"width": 1280, "height": 720},
            verbose=False,
        )

    async def scrape_jobs_async(self) -> List[JobListing]:
        """Asynchronously scrape LinkedIn job listings."""

        results: List[JobListing] = []
        crawler_config = self._create_crawler_config()
        detail_config = self._create_detail_crawler_config()

        try:
            async with AsyncWebCrawler() as crawler:
                for page in range(1, self.config.max_pages + 1):
                    if len(results) >= self.config.max_jobs:
                        break

                    search_url = self.build_search_url(page)
                    self.logger.info("Crawling %s", search_url)

                    crawl_result = await crawler.arun(url=search_url, config=crawler_config)
                    if not getattr(crawl_result, "success", False):
                        self.logger.warning("Failed to fetch LinkedIn page %s (%s)", page, search_url)
                        continue

                    page_jobs = self.parse_job_cards(crawl_result.html)
                    self.logger.info("Parsed %s LinkedIn jobs from page %s", len(page_jobs), page)

                    for job in page_jobs:
                        if len(results) >= self.config.max_jobs:
                            break

                        if job.job_url:
                            await self._enrich_job_listing(crawler, job, detail_config)

                        results.append(job)
        except Exception as exc:  # pragma: no cover - relies on remote services
            self.logger.error("Failed to crawl LinkedIn: %s", exc)
            raise

        return results[: self.config.max_jobs]

    async def _enrich_job_listing(
        self,
        crawler: AsyncWebCrawler,
        job: JobListing,
        config: CrawlerRunConfig,
    ) -> None:
        """Fetch the job detail page and enrich the listing."""

        if not job.job_url:
            return

        try:
            detail_result = await crawler.arun(url=job.job_url, config=config)
        except Exception as exc:  # pragma: no cover - depends on network
            self.logger.warning("Failed to fetch LinkedIn job detail for %s: %s", job.job_url, exc)
            return

        if not getattr(detail_result, "success", False):
            self.logger.warning("LinkedIn job detail crawl unsuccessful for %s", job.job_url)
            return

        self._parse_job_detail_page(job, detail_result.html)

    def scrape_jobs(self) -> List[Dict[str, Any]]:
        """Synchronously scrape jobs and return dictionaries."""

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
        """Parse LinkedIn search HTML and extract job listings."""

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        cards: List[Any] = []
        selectors = [
            "ul.jobs-search__results-list li",  # Primary LinkedIn layout
            "div.base-card",  # Fallback for card container
            "div.job-search-card",  # Legacy layout
        ]

        for selector in selectors:
            for card in soup.select(selector):
                if card not in cards:
                    cards.append(card)

        job_listings: List[JobListing] = []
        for card in cards:
            job = self._parse_job_card(card)
            if job:
                job_listings.append(job)

        return job_listings

    def _parse_job_card(self, card: Any) -> Optional[JobListing]:
        """Convert a LinkedIn job card element into a :class:`JobListing`."""

        title = self._select_text(card, [
            "h3.base-search-card__title",
            "h3.job-search-card__title",
            "a.job-card-list__title",
        ])
        if not title:
            return None

        company = self._select_text(card, [
            "h4.base-search-card__subtitle",
            "a.job-search-card__subtitle",
            "span.job-card-container__primary-description",
        ])
        location = self._select_text(card, [
            "span.job-search-card__location",
            "li.job-card-container__metadata-item",
        ])

        work_arrangement = self._select_text(card, [
            "span.job-card-container__metadata-item--workplace-type",
            "span.job-search-card__metadata-item",
        ])

        job_url = self._extract_job_url(card)
        job_id = self._extract_job_id(job_url)

        posted_at = None
        time_element = card.find("time")
        if time_element:
            posted_at = self._normalize_posted_at(
                time_element.get("datetime"),
                time_element.get("title"),
                time_element.get_text(strip=True),
            )

        company_url = self._extract_company_url(card)
        company_profile_url = self._extract_company_logo(card)

        job = JobListing(
            id=job_id,
            title=title,
            company=company,
            location=location,
            work_arrangement=work_arrangement,
            posted_at=posted_at,
            job_url=job_url,
            apply_url=job_url,
            company_url=company_url,
            company_profile_url=company_profile_url,
            source="LinkedIn",
        )
        return job

    def _parse_job_detail_page(self, job: JobListing, html: str) -> None:
        """Extract detailed information from the job detail page HTML."""

        if not html:
            return

        soup = BeautifulSoup(html, "lxml")

        description = self._select_text(
            soup,
            [
                "div.show-more-less-html__markup",
                "section.description__text",
                "div.jobs-description__content",
                "div.description__text",
            ],
            multiline=True,
        )
        if description:
            job.description = description

        work_type = self._select_text(
            soup,
            [
                "li[data-test-id='job-details-work-type']",
                "li[data-test-id='job-details-employment-type']",
                "li[data-test-id='job-details-job-type']",
            ],
        )
        if work_type:
            job.work_type = work_type

        work_arrangement = self._select_text(
            soup,
            [
                "li[data-test-id='job-details-workplace-type']",
                "span.jobs-unified-top-card__workplace-type",
            ],
        )
        if work_arrangement:
            job.work_arrangement = work_arrangement

        salary = self._select_text(
            soup,
            [
                "li[data-test-id='job-details-salary']",
                "span[data-test-id='salary']",
                "div.jobs-unified-top-card__salary-info",
            ],
        )
        if salary:
            job.salary = salary

        posted_at = self._select_text(
            soup,
            [
                "span.posted-time-ago__text",
                "span.jobs-unified-top-card__posted-date",
            ],
        )
        if posted_at:
            normalized = self._normalize_posted_at(posted_at)
            if normalized:
                job.posted_at = normalized

        apply_url = self._extract_apply_url(soup)
        if apply_url:
            job.apply_url = apply_url

        company_url = self._extract_company_detail_url(soup)
        if company_url:
            job.company_url = company_url

        company_logo = self._extract_company_logo(soup)
        if company_logo:
            job.company_profile_url = company_logo

        job.company_description = self._select_text(
            soup,
            [
                "section.jobs-company__company-details",
                "div.jobs-company__company-description",
                "div[data-test-id='about-company']",
            ],
            multiline=True,
        )

        job.requirements = self._extract_section_by_heading(
            soup,
            headings={"qualifications", "requirements", "what you'll need", "skills"},
        )

        job.benefits = self._extract_section_by_heading(
            soup,
            headings={"benefits", "what we offer", "perks"},
        )

        job.seniority_level = self._select_text(
            soup,
            [
                "li[data-test-id='job-details-seniority']",
                "li[data-test-id='job-details-experience']",
            ],
        )

        job.application_method = self._select_text(
            soup,
            [
                "button[data-tracking-control-name='public_jobs_apply-link-offsite']",
                "button.jobs-apply-button",
                "a[data-tracking-control-name='public_jobs_apply-link-offsite']",
            ],
        )

        if not job.id:
            job.id = self._extract_job_id(job.job_url)

    def save_results(
        self,
        jobs: Iterable[JobListing | Dict[str, Any]],
        output_path: os.PathLike[str] | str,
    ) -> Path:
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
        self.logger.info("Saved %s LinkedIn job(s) to %s", len(serializable), path)
        return path

    # --------------------------
    # Helper methods
    # --------------------------

    def _select_text(
        self,
        element: Any,
        selectors: Iterable[str],
        *,
        multiline: bool = False,
    ) -> Optional[str]:
        """Return cleaned text for the first selector that matches."""

        for selector in selectors:
            if not hasattr(element, "select_one"):
                continue
            node = element.select_one(selector)
            if not node:
                continue
            text = node.get_text("\n" if multiline else " ", strip=True)
            if text:
                return self._clean_multiline_text(text) if multiline else self._clean_text(text)
        return None

    def _extract_job_url(self, card: Any) -> Optional[str]:
        """Extract the job posting URL from a card."""

        link = None
        if hasattr(card, "select_one"):
            link = card.select_one("a.base-card__full-link") or card.select_one("a.job-card-list__title")
        if not link and hasattr(card, "find"):
            link = card.find("a", href=True)
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        return urljoin(self.ROOT_URL, href)

    @staticmethod
    def _extract_job_id(job_url: Optional[str]) -> Optional[str]:
        """Attempt to infer the LinkedIn job identifier from the job URL."""

        if not job_url:
            return None
        patterns = [
            r"/jobs/view/(\d+)",
            r"currentJobId=(\d+)",
            r"jobId=(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, job_url)
            if match:
                return match.group(1)
        return None

    def _extract_company_url(self, element: Any) -> Optional[str]:
        """Extract a company profile URL from a card or detail element."""

        link = None
        if hasattr(element, "select_one"):
            link = element.select_one("a[href*='/company/']")
        if not link and hasattr(element, "find"):
            link = element.find("a", href=re.compile(r"/company/"))
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        return urljoin(self.ROOT_URL, href)

    def _extract_company_logo(self, element: Any) -> Optional[str]:
        """Extract the company logo image URL."""

        image = None
        if hasattr(element, "select_one"):
            image = element.select_one("img.artdeco-entity-image") or element.select_one("img")
        if not image and hasattr(element, "find"):
            image = element.find("img")
        if not image:
            return None
        src = image.get("data-delayed-url") or image.get("data-src") or image.get("src")
        if not src:
            return None
        return urljoin(self.ROOT_URL, src)

    def _extract_apply_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the best apply URL from the detail page."""

        link = soup.select_one("a[data-tracking-control-name='public_jobs_apply-link-offsite']")
        if not link:
            link = soup.select_one("a.topcard__link")
        if link and link.get("href"):
            return urljoin(self.ROOT_URL, link.get("href"))
        return None

    def _extract_company_detail_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the company URL from the job detail page."""

        link = soup.select_one("a.topcard__org-name-link")
        if not link:
            link = soup.select_one("a[data-control-name='company_link']")
        if link and link.get("href"):
            return urljoin(self.ROOT_URL, link.get("href"))
        return None

    def _extract_section_by_heading(
        self,
        soup: BeautifulSoup,
        *,
        headings: Iterable[str],
    ) -> Optional[str]:
        """Extract text that follows a heading matching the provided keywords."""

        normalized_headings = {h.lower() for h in headings}
        for heading_tag in soup.find_all(["h2", "h3", "h4"]):
            heading_text = heading_tag.get_text(strip=True).lower()
            if heading_text in normalized_headings:
                content_parts: List[str] = []
                for sibling in heading_tag.next_siblings:
                    if isinstance(sibling, NavigableString):
                        text = str(sibling).strip()
                        if text:
                            content_parts.append(text)
                        continue
                    if isinstance(sibling, Tag) and sibling.name in {"h2", "h3", "h4"}:
                        break
                    if isinstance(sibling, Tag):
                        text = sibling.get_text("\n", strip=True)
                        if text:
                            content_parts.append(text)
                if content_parts:
                    combined = "\n".join(self._clean_multiline_text(part) for part in content_parts if part)
                    if combined:
                        return combined
        return None

    def _normalize_posted_at(self, *values: Optional[str]) -> Optional[str]:
        """Normalize posted date strings into ISO 8601 format when possible."""

        for value in values:
            if not value:
                continue
            parsed = self._parse_posted_timestamp(value)
            if parsed:
                return parsed

        for value in values:
            if value and value.strip():
                return value.strip()
        return None

    def _parse_posted_timestamp(self, raw: str) -> Optional[str]:
        """Parse relative or absolute LinkedIn timestamps into ISO strings."""

        text = raw.strip()
        if not text:
            return None

        # Handle ISO-like absolute dates first
        iso_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]
        for fmt in iso_formats:
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat(timespec="seconds")
            except ValueError:
                continue

        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass

        normalized = text.lower()
        now = datetime.now(timezone.utc)

        if normalized in {"new", "just posted"}:
            return now.isoformat(timespec="seconds")
        if normalized in {"within the past 24 hours", "past 24 hours"}:
            return (now - timedelta(hours=12)).isoformat(timespec="seconds")
        if "yesterday" in normalized:
            return (now - timedelta(days=1)).isoformat(timespec="seconds")

        match = re.search(
            r"(\d+)\s*(minute|minutes|min|mins|hour|hours|hr|hrs|day|days|week|weeks|month|months|year|years)\b",
            normalized,
        )
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            delta = self._timedelta_for_unit(unit, value)
            if delta:
                return (now - delta).isoformat(timespec="seconds")

        approx_match = re.search(
            r"within the past\s*(\d+)\s*(day|days|week|weeks)",
            normalized,
        )
        if approx_match:
            value = int(approx_match.group(1))
            unit = approx_match.group(2)
            delta = self._timedelta_for_unit(unit, value)
            if delta:
                return (now - delta / 2).isoformat(timespec="seconds")

        return None

    @staticmethod
    def _timedelta_for_unit(unit: str, value: int) -> Optional[timedelta]:
        """Create a :class:`timedelta` for the provided unit."""

        unit = unit.lower()
        if unit in {"minute", "minutes", "min", "mins"}:
            return timedelta(minutes=value)
        if unit in {"hour", "hours", "hr", "hrs"}:
            return timedelta(hours=value)
        if unit in {"day", "days"}:
            return timedelta(days=value)
        if unit in {"week", "weeks"}:
            return timedelta(weeks=value)
        if unit in {"month", "months"}:
            return timedelta(days=30 * value)
        if unit in {"year", "years"}:
            return timedelta(days=365 * value)
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        """Collapse excessive whitespace into single spaces."""

        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _clean_multiline_text(value: str) -> str:
        """Normalize multiline text while preserving logical breaks."""

        lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
        return "\n".join(line for line in lines if line)
