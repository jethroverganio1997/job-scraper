# LinkedIn Scraper Feature Plan

## Related Documentation
- [Architecture Overview](../system/architecture-overview.md)
- [Tech Stack](../system/tech-stack.md)
- [Job Scraper System](../system/job-scraper-system.md)

## Objective
Add a Crawl4AI-powered LinkedIn scraping module that mirrors the existing `JobListing` JSON schema and allows runtime configuration through environment variables.

## Plan
1. **Create LinkedIn scraper module**
   - Implement `LinkedInScraper` in `src/linkedin_scraper.py` using Crawl4AI to fetch search result pages and job detail pages without login.
   - Reuse the shared `JobListing` structure to ensure identical JSON output fields.
   - Support pagination and time filters similar to the provided Playwright example.
2. **Parameterize via environment variables**
   - Load defaults from `.env` values (keywords, location, max pages, max jobs, time filter).
   - Update `.env.example` with new configuration keys.
3. **Expose execution entry point**
   - Provide a CLI runner (e.g., `main_linkedin.py` or update `main.py`) that instantiates the LinkedIn scraper and persists JSON output mirroring the Seek workflow.
   - Ensure output is saved under `result/` with a descriptive filename and printed to stdout.
4. **Documentation updates**
   - Extend `.agent/system` docs to describe the new LinkedIn scraper component and configuration knobs.
   - Update `.agent/README.md` to reference the new task document.
5. **Validation**
   - Execute `python -m compileall` for the updated modules to catch syntax issues, acknowledging that live scraping cannot run in CI.

## Risks & Mitigations
- **LinkedIn anti-bot measures**: Use realistic user agent headers and fallback parsing strategies to handle missing selectors.
- **Dynamic HTML structure changes**: Implement multiple selector fallbacks and graceful degradation when fields are absent.
- **Unauthenticated access limitations**: Restrict to public listings and guard network failures with logging.

## Outcome
- Added `LinkedInScraper` module with Crawl4AI-powered search and detail enrichment pipelines.
- Extended `JobListing` dataclass to capture requirements, benefits, company description, application method, and seniority level.
- Introduced `linkedin_main.py` CLI entry point and new `LINKEDIN_*` environment variables.
- Updated documentation to cover LinkedIn architecture, selectors, and configuration knobs.
