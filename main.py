#!/usr/bin/env python3
"""Job Scraper - A web scraping tool for job listings."""

from src import JobScraper


def main() -> None:
    """Main entry point for the job scraper application."""
    print("Job Scraper - Starting...")

    scraper = JobScraper()

    try:
        jobs = scraper.scrape_jobs()
    except Exception as exc:  # pragma: no cover - depends on external services
        print("Failed to scrape jobs:", exc)
        print("Ensure the required Playwright browsers are installed by running `playwright install`.")
        return

    if not jobs:
        print("No job listings found. Adjust your SEEK_* environment variables and try again.")
        return

    print(f"Retrieved {len(jobs)} Seek job(s):")
    for job in jobs:
        title = job.get("title", "Unknown Title")
        company = job.get("company") or "Unknown Company"
        location = job.get("location") or "Unknown Location"
        print(f"- {title} — {company} ({location})")
        if job.get("job_url"):
            print(f"  URL: {job['job_url']}")
        if job.get("salary"):
            print(f"  Salary: {job['salary']}")
        if job.get("listing_date"):
            print(f"  Listed: {job['listing_date']}")
        if job.get("summary"):
            print(f"  Summary: {job['summary']}")


if __name__ == "__main__":
    main()
