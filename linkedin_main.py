#!/usr/bin/env python3
"""LinkedIn job scraper CLI entry point."""

import json
from pathlib import Path

from src import LinkedInScraper


def main() -> None:
    """Main entry point for scraping LinkedIn job listings."""

    print("LinkedIn Job Scraper - Starting...")

    scraper = LinkedInScraper()

    try:
        jobs = scraper.scrape_jobs()
    except Exception as exc:  # pragma: no cover - depends on external services
        print("Failed to scrape LinkedIn jobs:", exc)
        print("Ensure Crawl4AI dependencies and browsers are installed and that LinkedIn is reachable.")
        return

    if not jobs:
        print("No LinkedIn job listings found. Adjust your LINKEDIN_* environment variables and try again.")
        return

    output_path = scraper.save_results(jobs, Path("result/linkedin_jobs.json"))
    print(f"Saved {len(jobs)} LinkedIn job(s) to {output_path}")
    print(json.dumps(jobs, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
