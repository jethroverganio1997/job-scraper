# Job Scraper System Documentation

## Related Documentation
- [Architecture Overview](architecture-overview.md)
- [Tech Stack](tech-stack.md)

## System Purpose

The Job Scraper System is a specialized web scraping application designed to extract job listings from SEEK.com.au, one of Australia's leading job boards. The system focuses on software engineering positions and provides structured data output for further analysis and processing.

## Core Components

### 1. JobListing Data Model
**Location**: `src/scraper.py:15-48`

The `JobListing` dataclass represents the canonical data structure for job information:

```python
@dataclass
class JobListing:
    id: Optional[str]              # Unique job identifier
    title: Optional[str]           # Job title
    company: Optional[str]         # Company name
    company_url: Optional[str]     # Company website
    company_profile_url: Optional[str]  # Company profile page
    location: Optional[str]        # Job location
    work_type: Optional[str]       # Employment type (full-time, part-time, etc.)
    work_arrangement: Optional[str]  # Work arrangement (remote, hybrid, etc.)
    salary: Optional[str]          # Salary information
    description: Optional[str]     # Full job description
    posted_at: Optional[str]       # Posting date/time
    apply_url: Optional[str]       # Direct application URL
    job_url: Optional[str]         # Job listing URL
    source: str = "Seek"           # Data source identifier
```

**Key Features**:
- **Type Safety**: Optional fields with type hints
- **JSON Serialization**: `to_dict()` method for output
- **Source Tracking**: Identifies data origin
- **Comprehensive Coverage**: All relevant job metadata

### 2. JobScraper Engine
**Location**: `src/scraper.py:50-759`

The main scraping engine responsible for data extraction and processing.

#### Configuration Management
- **Environment Variables**: Load from `.env` file
- **Parameter Validation**: Runtime validation with defaults
- **Search Configuration**: Keywords, location, pagination, date filters

**Configuration Parameters**:
```python
SEEK_KEYWORDS="software engineer"    # Search keywords
SEEK_LOCATION="Philippines"          # Job location filter
SEEK_MAX_JOBS=5                      # Maximum jobs to scrape
SEEK_MAX_PAGES=3                     # Maximum pages to process
SEEK_DATE_FILTER=1                   # Date filter (1=today, 3=3days, etc.)
```

#### URL Construction System
- **Base URL**: `https://www.seek.com.au/jobs`
- **Query Parameters**: Keywords, location, date range, pagination
- **Dynamic Generation**: Configurable search criteria

**URL Structure**:
```
https://www.seek.com.au/jobs?keywords={keywords}&where={location}&page={page}&date={days}
```

#### Scraping Pipeline

**Stage 1: Search Page Processing**
- Fetch search result pages using Crawl4AI
- Extract job cards with multiple CSS selectors
- Parse basic job information (title, company, location)

**Stage 2: Detail Page Enrichment**
- Fetch individual job listing pages
- Extract comprehensive job details
- Apply Schema.org structured data extraction

**Stage 3: Data Processing**
- Normalize and clean extracted data
- Convert relative dates to ISO 8601 format
- Apply validation and business rules

### 3. Data Processing Pipeline

#### Date Normalization System
**Location**: `src/scraper.py:600-650`

Converts various relative date formats to ISO 8601 timestamps:

```python
# Examples of conversions
"17 min ago"    → "2025-01-17T14:30:00Z"
"3h ago"        → "2025-01-17T11:30:00Z"
"2d ago"        → "2025-01-15T14:30:00Z"
"1w ago"        → "2025-01-10T14:30:00Z"
```

**Supported Time Units**:
- Minutes: `min`, `minute`, `minutes`
- Hours: `h`, `hr`, `hour`, `hours`
- Days: `d`, `day`, `days`
- Weeks: `w`, `wk`, `week`, `weeks`
- Months: `mo`, `mth`, `month`, `months`
- Years: `y`, `yr`, `year`, `years`

#### Schema.org Integration
**Location**: `src/scraper.py:500-580`

Extracts structured data from JSON-LD scripts embedded in job pages:

```python
# Example Schema.org extraction
{
    "@context": "https://schema.org",
    "@type": "JobPosting",
    "title": "Software Engineer",
    "hiringOrganization": {
        "@type": "Organization",
        "name": "Tech Company"
    },
    "datePosted": "2025-01-17",
    "description": "Full job description..."
}
```

#### Text Cleaning System
**Location**: `src/scraper.py:700-750`

Normalizes text content for consistent output:

- **Whitespace Normalization**: Remove excess whitespace
- **HTML Tag Removal**: Strip remaining HTML tags
- **Character Encoding**: Handle special characters properly
- **Content Structuring**: Format descriptions for readability

### 4. Async Architecture

#### AsyncWebCrawler Integration
- **Concurrent Processing**: Multiple pages processed simultaneously
- **Non-blocking I/O**: Efficient network operations
- **Event Loop Management**: Proper async context handling

#### Async Job Detail Fetching
```python
# Concurrent fetching of job detail pages
async def fetch_job_details(job_urls: List[str]) -> List[JobListing]:
    tasks = [fetch_single_job(url) for url in job_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return process_results(results)
```

## Data Flow Architecture

### 1. Initialization Phase
```
Load .env → Validate parameters → Initialize logger → Create scraper instance
```

### 2. Search Phase
```
Build search URL → Fetch search page → Extract job cards → Collect job URLs
```

### 3. Enrichment Phase
```
Fetch detail pages → Extract comprehensive data → Apply Schema.org processing → Normalize data
```

### 4. Processing Phase
```
Date normalization → Text cleaning → Validation → Quality checks
```

### 5. Output Phase
```
Convert to JSON → Save to file → Generate summary → Complete execution
```

## CSS Selector Strategy

### Search Page Selectors
**Location**: `src/scraper.py:200-250`

Multiple selector strategies for robustness:

```python
# Primary selectors (current SEEK layout)
JOB_CARD_SELECTORS = [
    "[data-automation='searchResults'] article",
    ".y735df0._12Fs8vG4GnyCewh_VJq0Ls",
    "article[data-automation='normalJob']"
]

# Job data selectors
TITLE_SELECTORS = ["[data-automation='jobTitle']", "a[data-automation='job-link'] span"]
COMPANY_SELECTORS = ["[data-automation='jobCompany']", "span[data-automation='job-company']"]
LOCATION_SELECTORS = ["[data-automation='jobLocation']", "span[data-automation='job-location']"]
```

### Detail Page Selectors
**Location**: `src/scraper.py:300-350`

```python
# Comprehensive job detail extraction
DESCRIPTION_SELECTORS = [
    "[data-automation='jobAdDetails']",
    ".y735df0._1JtWslb4uIaFd6u0VQ7Hr0",
    "div[data-automation='jobDescription']"
]

SALARY_SELECTORS = [
    "[data-automation='jobSalary']",
    "span[data-automation='job-salary']",
    ".y735df0._1TJ0c_7f2oRvPZMh6F4Qa2"
]
```

## Error Handling Strategy

### Network Error Handling
- **Retry Mechanism**: Exponential backoff for failed requests
- **Timeout Management**: Configurable request timeouts
- **Connection Recovery**: Handle network interruptions gracefully
- **Fallback Strategies**: Alternative selectors and parsing methods

### Data Validation
- **Completeness Checks**: Ensure required fields are present
- **Format Validation**: Validate data formats and types
- **Business Rule Validation**: Apply domain-specific rules
- **Quality Assurance**: Data quality scoring and filtering

### Error Recovery
```python
# Example error handling pattern
try:
    result = await fetch_page(url)
except NetworkError as e:
    logger.warning(f"Network error for {url}: {e}")
    return await retry_with_backoff(url, max_retries=3)
except ParseError as e:
    logger.error(f"Parse error for {url}: {e}")
    return None
```

## Output System

### JSON Output Format
**Location**: `result/seek_jobs.json`

```json
{
    "scrape_date": "2025-01-17T14:30:00Z",
    "search_parameters": {
        "keywords": "software engineer",
        "location": "Philippines",
        "max_jobs": 5,
        "date_filter": 1
    },
    "jobs": [
        {
            "id": "job123456",
            "title": "Senior Software Engineer",
            "company": "Tech Corp",
            "location": "Manila, Philippines",
            "work_type": "Full-time",
            "salary": "₱80,000 - ₱120,000 per month",
            "description": "Full job description...",
            "posted_at": "2025-01-17T10:30:00Z",
            "apply_url": "https://www.seek.com.au/job/123456",
            "job_url": "https://www.seek.com.au/job/123456",
            "source": "Seek"
        }
    ],
    "summary": {
        "total_jobs_found": 5,
        "successful_extractions": 5,
        "failed_extractions": 0
    }
}
```

### Console Output
- **Progress Updates**: Real-time progress information
- **Error Reporting**: Detailed error messages
- **Summary Statistics**: Final execution summary
- **Performance Metrics**: Execution time and success rates

## Performance Characteristics

### Concurrent Processing
- **Async Architecture**: Multiple pages processed simultaneously
- **Resource Efficiency**: Optimal memory and CPU usage
- **Network Utilization**: Efficient HTTP connection management

### Caching Strategy
- **Local Caching**: Temporary caching of parsed data
- **Session Management**: Reuse HTTP connections
- **Memory Optimization**: Efficient data structures

### Rate Limiting
- **Polite Crawling**: Respectful request intervals
- **Configurable Delays**: Adjustable timing between requests
- **User Agent Management**: Proper identification

## Security Considerations

### Data Privacy
- **No Credential Storage**: Secure environment variable management
- **Input Sanitization**: Clean and validate all inputs
- **Output Filtering**: Remove sensitive information from output

### Request Security
- **User Agent Headers**: Proper browser identification
- **Request Headers**: Standard HTTP headers for legitimacy
- **Session Management**: Secure connection handling

## Monitoring and Logging

### Logging System
- **Structured Logging**: Consistent log format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **File Logging**: Persistent log storage
- **Console Output**: Real-time log display

### Performance Monitoring
- **Execution Metrics**: Time tracking for operations
- **Success Rates**: Monitoring extraction success
- **Error Tracking**: Detailed error logging
- **Resource Usage**: Memory and CPU monitoring

## Integration Points

### Current Integrations
- **SEEK.com.au**: Primary job board target
- **Crawl4AI**: Scraping framework integration
- **OpenAI**: Optional AI features (configured but not active)

### Future Integration Points
- **Additional Job Boards**: LinkedIn, Indeed, Glassdoor
- **Database Systems**: SQLite, PostgreSQL integration
- **API Layer**: REST API for external access
- **Monitoring Systems**: Enhanced logging and metrics

## Maintenance and Updates

### Selector Maintenance
- **Regular Updates**: Monitor for website layout changes
- **Fallback Selectors**: Multiple selector strategies
- **Automated Testing**: Validate extraction accuracy
- **Version Control**: Track changes and rollbacks

### Dependency Management
- **Regular Updates**: Keep dependencies current
- **Security Patches**: Apply security updates promptly
- **Compatibility Testing**: Test with new versions
- **Documentation**: Update documentation with changes