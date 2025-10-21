#!/usr/bin/env python3
"""
Job Scraper - A web scraping tool for job listings
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper import JobScraper

def main():
    """Main entry point for the job scraper application."""
    print("Job Scraper - Starting...")

    scraper = JobScraper()

    # Example usage - will be expanded
    print("Job Scraper initialized successfully!")
    print("Use the scraper to find job listings from various job boards.")

if __name__ == "__main__":
    main()