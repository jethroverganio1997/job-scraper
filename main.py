#!/usr/bin/env python3
"""Job Scraper - A web scraping tool for job listings."""

import json
from pathlib import Path

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

    output_path = scraper.save_results(jobs, Path("result/seek_jobs.json"))
    print(f"Saved {len(jobs)} Seek job(s) to {output_path}")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
