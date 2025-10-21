# Job-Scraper Documentation

This documentation provides comprehensive information about the Job-Scraper system, a Python-based web scraping application for extracting job listings from SEEK.com.au.

## Documentation Structure

### 📋 System Documentation
**Location**: `.agent/system/`

Current state and architecture documentation for understanding how the system works.

- **[Architecture Overview](system/architecture-overview.md)** - High-level system architecture, components, data flow, and design patterns
- **[Tech Stack](system/tech-stack.md)** - Complete technology stack, dependencies, and technical decisions
- **[Job Scraper System](system/job-scraper-system.md)** - Detailed system components, data models, and processing pipeline

### 📝 Tasks Documentation
**Location**: `.agent/tasks/`

Product Requirements Documents (PRDs) and implementation plans for features.

*No task documents currently exist.*

### 🔧 SOP Documentation
**Location**: `.agent/sop/`

Standard Operating Procedures and best practices for executing tasks.

*No SOP documents currently exist.*

## Quick Start

### For New Engineers

1. **Start with System Overview**: Read [`system/architecture-overview.md`](system/architecture-overview.md) to understand the high-level system design
2. **Understand Technology Stack**: Review [`system/tech-stack.md`](system/tech-stack.md) for dependencies and technical decisions
3. **Dive into Implementation**: Study [`system/job-scraper-system.md`](system/job-scraper-system.md) for detailed component information

### For Feature Development

1. **Review Architecture**: Understand current system design and patterns
2. **Check Technology Stack**: Ensure compatibility with existing dependencies
3. **Follow Data Models**: Use existing `JobListing` structure for consistency

### For Maintenance

1. **Monitor Selectors**: Regular checks for website layout changes
2. **Update Dependencies**: Keep all packages current
3. **Review Logs**: Monitor extraction success rates and errors

## System Overview

The Job-Scraper is a Python application that:

- **Scrapes** job listings from SEEK.com.au
- **Processes** and normalizes job data
- **Outputs** structured JSON data
- **Handles** date conversion and text cleaning
- **Supports** configurable search parameters

### Key Features

- **Async Architecture**: Efficient concurrent processing
- **Robust Parsing**: Multiple CSS selector strategies
- **Data Normalization**: Date conversion and text cleaning
- **Schema.org Integration**: Structured data extraction
- **Environment Configuration**: Flexible parameter management

### Core Components

- **JobListing Model**: Standardized job data structure
- **JobScraper Engine**: Main scraping and processing logic
- **Async Pipeline**: Concurrent page processing
- **Output System**: JSON file generation and console feedback

## Getting Started

### Prerequisites
- Python 3.13+
- Virtual environment
- Playwright browsers (`playwright install`)

### Setup Steps
1. Clone repository
2. Create virtual environment
3. Install dependencies (`pip install -r requirements.txt`)
4. Copy `.env.example` to `.env` and configure
5. Run `python main.py`

### Configuration
Key environment variables in `.env`:
```bash
SEEK_KEYWORDS=software engineer    # Search keywords
SEEK_LOCATION=Philippines          # Job location
SEEK_MAX_JOBS=5                    # Maximum jobs to scrape
SEEK_MAX_PAGES=3                   # Maximum pages to process
SEEK_DATE_FILTER=1                 # Date filter (1=today, 3=3days, etc.)
```

## Development Guidelines

### Code Organization
- Main logic in `src/scraper.py`
- Entry point in `main.py`
- Configuration via environment variables
- Output to `result/` directory

### Best Practices
- Use async patterns for network operations
- Implement proper error handling
- Validate all external data
- Log important operations and errors
- Use type hints for better code quality

### Adding Features
1. Understand existing data models and patterns
2. Follow async architecture for network operations
3. Update configuration management if needed
4. Add comprehensive error handling
5. Update relevant documentation

## Maintenance

### Regular Tasks
- Monitor SEEK.com.au for layout changes
- Update CSS selectors as needed
- Keep dependencies current
- Review and update documentation
- Monitor extraction success rates

### Troubleshooting
- Check logs for extraction errors
- Validate selector patterns
- Test with different search parameters
- Verify network connectivity
- Review environment configuration

## Contributing to Documentation

When adding new documentation:

1. **Determine Location**: Choose appropriate folder (`tasks/`, `system/`, or `sop/`)
2. **Use Kebab-Case**: File names should be `kebab-case.md`
3. **Link Related Docs**: Include cross-references at the top
4. **Update README**: Add new files to this index
5. **Follow Standards**: Use established formatting and structure

### Documentation Template
```markdown
# Document Title

## Related Documentation
- [Related Doc 1](../folder/file.md)
- [Related Doc 2](file.md)

## Content sections...

## Additional sections...
```

## Document Index

### System Documentation (3 files)
| Document | Purpose | Last Updated |
|----------|---------|--------------|
| [Architecture Overview](system/architecture-overview.md) | High-level system architecture and design | 2025-01-17 |
| [Tech Stack](system/tech-stack.md) | Technology dependencies and decisions | 2025-01-17 |
| [Job Scraper System](system/job-scraper-system.md) | Detailed system components and processing | 2025-01-17 |

### Tasks Documentation (1 file)
| Document | Purpose | Status |
|----------|---------|--------|
| [LinkedIn Scraper Feature Plan](tasks/linkedin-scraper.md) | Implementation approach for Crawl4AI LinkedIn scraper | Completed |

### SOP Documentation (0 files)
| Document | Purpose | Status |
|----------|---------|--------|
| *No SOP documents* | *No procedures documented* | *N/A* |

---

**Last Updated**: 2025-02-15
**Documentation Version**: 1.1
**Project**: Job-Scraper

For questions or contributions to documentation, please follow the contributing guidelines above.