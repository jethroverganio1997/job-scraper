"""Seek job scraper powered by Crawl4AI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from dotenv import load_dotenv


@dataclass
class JobListing:
    """Representation of a single job scraped from Seek."""

    id: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    company_url: Optional[str] = None
    company_profile_url: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    work_arrangement: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[str] = None
    apply_url: Optional[str] = None
    job_url: Optional[str] = None
    source: str = "Seek"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the job listing into a JSON-friendly dictionary."""

        def clean(value: Any) -> Any:
            if value is None:
                return ""
            if isinstance(value, str):
                return value.strip()
            return value

        return {
            "id": clean(self.id),
            "title": clean(self.title),
            "company": clean(self.company),
            "companyUrl": clean(self.company_url),
            "companyProfileUrl": clean(self.company_profile_url),
            "location": clean(self.location),
            "workType": clean(self.work_type),
            "workArrangement": clean(self.work_arrangement),
            "salary": clean(self.salary),
            "description": clean(self.description),
            "postedAt": clean(self.posted_at),
            "applyUrl": clean(self.apply_url),
            "jobUrl": clean(self.job_url),
            "source": clean(self.source),
        }


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

    def _create_detail_crawler_config(self) -> CrawlerRunConfig:
        """Create the Crawl4AI configuration for individual job detail pages."""

        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="domcontentloaded",
            parser_type="lxml",
            verbose=False,
        )

    async def scrape_jobs_async(self) -> List[JobListing]:
        """Asynchronously scrape Seek job listings based on the configured parameters."""

        results: List[JobListing] = []
        crawler_config = self._create_crawler_config()
        detail_config = self._create_detail_crawler_config()

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
                        if len(results) >= self.max_jobs:
                            break

                        if job.job_url:
                            await self._enrich_job_listing(crawler, job, detail_config)

                        results.append(job)
        except Exception as exc:  # pragma: no cover - relies on runtime dependencies
            self.logger.error("Failed to crawl Seek: %s", exc)
            raise

        return results[: self.max_jobs]

    async def _enrich_job_listing(
        self,
        crawler: AsyncWebCrawler,
        job: JobListing,
        config: CrawlerRunConfig,
    ) -> None:
        """Fetch and parse the job detail page to enrich the listing."""

        try:
            detail_result = await crawler.arun(url=job.job_url, config=config)
        except Exception as exc:  # pragma: no cover - depends on remote site
            self.logger.warning("Failed to fetch job detail for %s: %s", job.job_url, exc)
            return

        if not getattr(detail_result, "success", False):
            self.logger.warning("Job detail crawl unsuccessful for %s", job.job_url)
            return

        self._parse_job_detail_page(job, detail_result.html)

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
        posted_at = self._extract_text(card, ["jobListingDate", "jobCardDate", "listing-date"])
        description = self._extract_text(card, ["jobShortDescription", "job-short-description"])
        job_url = self._extract_job_url(card)
        job_id = self._extract_job_id(card) or self._derive_job_id_from_url(job_url)

        return JobListing(
            id=job_id,
            title=title,
            company=company,
            location=location,
            salary=salary,
            posted_at=posted_at,
            description=description,
            job_url=job_url,
        )

    def _parse_job_detail_page(self, job: JobListing, html: str) -> None:
        """Extract detailed information from the job detail page HTML."""

        if not html:
            return

        soup = BeautifulSoup(html, "lxml")

        schema = self._extract_job_schema(soup)
        if schema:
            self._apply_job_schema_data(job, schema)

        title = self._extract_text(soup, ["job-detail-title", "jobTitle", "job-title"])
        if title:
            job.title = title

        company = self._extract_text(soup, ["job-detail-company-name", "jobCompany", "company-name"])
        if company:
            job.company = company

        company_link = self._find_by_data_automation(soup, ["job-detail-company-name", "jobCompany"], tag="a")
        if company_link and company_link.get("href"):
            job.company_url = urljoin(self.SEEK_ROOT_URL, company_link.get("href"))

        company_logo = self._find_by_data_automation(soup, ["jobCompanyLogo", "company-logo"], tag="img")
        if company_logo and company_logo.get("src"):
            job.company_profile_url = urljoin(self.SEEK_ROOT_URL, company_logo.get("src"))

        location = self._extract_text(soup, ["job-detail-location", "jobLocation", "location"])
        if location:
            job.location = location

        work_type = self._extract_text(soup, ["job-detail-work-type", "work-type"])
        if work_type:
            job.work_type = work_type

        work_arrangement = self._extract_text(
            soup,
            ["job-detail-work-arrangements", "job-detail-work-mode", "work-arrangements"],
        )
        if work_arrangement:
            job.work_arrangement = work_arrangement

        salary = self._extract_text(soup, ["job-detail-salary", "jobSalary", "salary"])
        if salary:
            job.salary = salary

        posted_at = self._extract_text(soup, ["job-detail-date", "jobListingDate", "listing-date"])
        if posted_at:
            job.posted_at = posted_at

        description_element = self._find_by_data_automation(
            soup,
            ["jobAdDetails", "job-detail-description", "jobAdContent"],
        )
        if not description_element:
            description_element = soup.find(id="job-details")
        if description_element:
            job.description = self._clean_description_text(description_element)

        apply_button = self._find_by_data_automation(
            soup,
            ["jobdetail-applybutton", "job-detail-apply", "apply-button"],
            tag="a",
        )
        if apply_button and apply_button.get("href"):
            job.apply_url = urljoin(self.SEEK_ROOT_URL, apply_button.get("href"))

        if not job.id:
            job.id = self._extract_text(soup, ["job-detail-id"]) or self._derive_job_id_from_url(job.job_url)

        if not job.job_url:
            canonical = soup.find("link", rel="canonical")
            if canonical and canonical.get("href"):
                job.job_url = canonical.get("href")

    def _extract_text(self, card: Any, automation_keys: Iterable[str]) -> Optional[str]:
        """Retrieve text content for a series of `data-automation` keys."""

        element = self._find_by_data_automation(card, automation_keys)
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

    def _find_by_data_automation(
        self,
        element: Any,
        automation_keys: Iterable[str],
        *,
        tag: Optional[str] = None,
    ) -> Optional[Any]:
        """Locate the first element matching any of the provided automation keys."""

        if element is None:
            return None

        for key in automation_keys:
            attrs = {"data-automation": key}
            found = element.find(tag, attrs=attrs) if tag else element.find(attrs=attrs)
            if found:
                return found
        return None

    def _clean_description_text(self, element: Any) -> str:
        """Normalise the textual content for long-form descriptions."""

        text = element.get_text("\n", strip=True)
        return self._normalize_whitespace(text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Collapse redundant whitespace while preserving paragraph breaks."""

        if not text:
            return ""

        normalized = re.sub(r"\r\n?", "\n", text)
        normalized = normalized.replace("\u00a0", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n\s+", "\n", normalized)
        normalized = re.sub(r"\s+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _extract_job_schema(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Retrieve the JobPosting schema block from the detail page."""

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            content = script.string or script.get_text() or ""
            if not content.strip():
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in {"JobPosting", "JobPostingSeries"}:
                    return item
        return None

    def _apply_job_schema_data(self, job: JobListing, schema: Dict[str, Any]) -> None:
        """Enrich the job listing using JSON-LD schema information."""

        identifier = schema.get("identifier")
        if isinstance(identifier, dict):
            candidate_id = identifier.get("value") or identifier.get("@id") or identifier.get("name")
            if candidate_id and not job.id:
                job.id = str(candidate_id)
        elif isinstance(identifier, str) and not job.id:
            job.id = identifier

        job.title = job.title or schema.get("title") or schema.get("name") or job.title

        hiring_org = schema.get("hiringOrganization")
        if isinstance(hiring_org, dict):
            job.company = job.company or hiring_org.get("name") or job.company
            company_url = hiring_org.get("sameAs") or hiring_org.get("url")
            if company_url and not job.company_url:
                job.company_url = company_url
            logo = hiring_org.get("logo")
            if isinstance(logo, dict):
                logo_url = logo.get("url")
            else:
                logo_url = logo
            if logo_url and not job.company_profile_url:
                job.company_profile_url = logo_url

        location = self._format_schema_location(schema.get("jobLocation"))
        if location and not job.location:
            job.location = location

        work_type = schema.get("employmentType")
        if work_type and not job.work_type:
            job.work_type = work_type

        work_arrangement = schema.get("jobLocationType") or schema.get("workHours")
        if work_arrangement and not job.work_arrangement:
            job.work_arrangement = work_arrangement

        salary = self._format_schema_salary(schema.get("baseSalary"))
        if salary and not job.salary:
            job.salary = salary

        description = schema.get("description")
        if description and not job.description:
            if isinstance(description, str) and "<" in description:
                desc_soup = BeautifulSoup(description, "lxml")
                job.description = self._clean_description_text(desc_soup)
            elif isinstance(description, str):
                job.description = self._normalize_whitespace(description)

        posted_at = schema.get("datePosted")
        if posted_at and not job.posted_at:
            job.posted_at = posted_at

        apply_url = schema.get("applicationLink")
        if not apply_url:
            application_contact = schema.get("applicationContact")
            if isinstance(application_contact, dict):
                apply_url = application_contact.get("url") or application_contact.get("email")
        if apply_url and not job.apply_url:
            job.apply_url = apply_url

        if not job.job_url and schema.get("url"):
            job.job_url = schema.get("url")

    def _format_schema_location(self, location_data: Any) -> Optional[str]:
        """Convert schema.org jobLocation data into a readable string."""

        if not location_data:
            return None

        if isinstance(location_data, list):
            parts = [self._format_schema_location(item) for item in location_data]
            deduped = [part for part in parts if part]
            if deduped:
                seen = []
                for part in deduped:
                    if part not in seen:
                        seen.append(part)
                return ", ".join(seen)
            return None

        if isinstance(location_data, dict):
            if "address" in location_data and isinstance(location_data["address"], dict):
                return self._format_schema_location(location_data["address"])

            components: List[str] = []
            for key in ("addressLocality", "addressRegion", "postalCode", "addressCountry"):
                value = location_data.get(key)
                if value:
                    components.append(str(value))

            if components:
                return ", ".join(components)

            if location_data.get("name"):
                return str(location_data.get("name"))

            return None

        if isinstance(location_data, str):
            return location_data.strip()

        return None

    def _format_schema_salary(self, salary_data: Any) -> Optional[str]:
        """Convert schema.org baseSalary data into readable text."""

        if not salary_data:
            return None

        if isinstance(salary_data, str):
            return salary_data.strip()

        if isinstance(salary_data, dict):
            currency = salary_data.get("currency") or salary_data.get("currencyCode")
            unit = salary_data.get("unitText")
            value = salary_data.get("value")

            range_text: Optional[str] = None
            if isinstance(value, dict):
                min_value = value.get("minValue")
                max_value = value.get("maxValue")
                if min_value and max_value:
                    range_text = f"{self._format_salary_number(min_value)} – {self._format_salary_number(max_value)}"
                elif min_value is not None:
                    range_text = self._format_salary_number(min_value)
                elif max_value is not None:
                    range_text = self._format_salary_number(max_value)
                if not unit and value.get("unitText"):
                    unit = value.get("unitText")
            elif value is not None:
                range_text = self._format_salary_number(value)

            parts: List[str] = []
            if range_text:
                parts.append(range_text)
            if unit:
                parts.append(str(unit))
            if currency:
                parts.append(f"({currency})")

            if parts:
                return " ".join(parts).strip()

        return None

    @staticmethod
    def _format_salary_number(value: Any) -> str:
        """Format numeric salary values with grouping separators."""

        if isinstance(value, (int, float)):
            if isinstance(value, float) and not value.is_integer():
                return f"{value:,.2f}"
            return f"{int(value):,}"
        return str(value)

    @staticmethod
    def _derive_job_id_from_url(job_url: Optional[str]) -> Optional[str]:
        """Attempt to infer the job identifier from the job URL."""

        if not job_url:
            return None

        match = re.search(r"/job/([\w-]+)", job_url)
        if match:
            return match.group(1)
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
