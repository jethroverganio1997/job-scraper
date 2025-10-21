# Architecture Overview

## Related Documentation
- [Tech Stack](tech-stack.md)
- [Job Scraper System](job-scraper-system.md)

## Project Overview

The **Job-Scraper** is a Python-based web scraping application designed to extract job listings from SEEK.com.au, one of Australia's leading job boards. The project focuses on software engineering jobs and outputs structured JSON data for further processing.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Configuration │    │   Web Scraping   │    │   Data Output   │
│                 │    │                  │    │                 │
│ • .env file     │───▶│ • Crawl4AI       │───▶│ • JSON files    │
│ • Parameters    │    │ • BeautifulSoup  │    │ • Console output│
│ • Validation    │    │ • Playwright     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Data Processing│
                       │                  │
                       │ • Normalization  │
                       │ • Date parsing   │
                       │ • Schema.org     │
                       │ • Cleaning       │
                       └──────────────────┘
```

## Core Components

### 1. Configuration Layer
- **Environment Variables**: `.env` file for API keys and parameters
- **Parameter Validation**: Runtime validation with sensible defaults
- **Search Configuration**: Keywords, location, pagination, date filters

### 2. Scraping Layer
- **Crawl4AI Engine**: Modern async web scraping framework
- **BeautifulSoup**: HTML parsing and data extraction
- **Playwright**: Browser automation for complex scenarios
- **Multi-Selector Strategy**: Resilient CSS selectors for DOM changes

### 3. Data Processing Layer
- **JobListing Model**: Standardized data structure with dataclass
- **Date Normalization**: Relative timestamps to ISO 8601
- **Schema.org Integration**: JSON-LD structured data extraction
- **Text Cleaning**: Whitespace normalization and content sanitization

### 4. Output Layer
- **JSON Serialization**: Structured data output
- **File Persistence**: Results saved to `result/` directory
- **Console Feedback**: Real-time progress updates

## Data Flow

### 1. Initialization
```
Load .env → Parse parameters → Validate configuration → Initialize scraper
```

### 2. URL Construction
```
Build search URL → Add query parameters → Generate pagination URLs
```

### 3. Scraping Process
```
Search page crawl → Extract job cards → Fetch detail pages → Parse comprehensive data
```

### 4. Data Processing
```
Schema.org extraction → Date normalization → Text cleaning → Validation
```

### 5. Output Generation
```
Convert to dict → Save to JSON → Console summary → Completion
```

## Key Design Patterns

### 1. Async Architecture
- **AsyncWebCrawler**: Concurrent page processing
- **Event Loop Management**: Proper async context handling
- **Non-blocking I/O**: Efficient network operations

### 2. Strategy Pattern
- **Multiple Selectors**: Fallback CSS selectors for robustness
- **Configurable Parameters**: Runtime behavior modification
- **Extensible Design**: Easy addition of new job boards

### 3. Data Model Pattern
- **JobListing Dataclass**: Type-safe data structure
- **JSON Serialization**: Consistent output format
- **Validation Methods**: Built-in data integrity

## Error Handling Strategy

### 1. Network Errors
- Retry mechanisms with exponential backoff
- Timeout handling and connection management
- Graceful degradation on partial failures

### 2. Parsing Errors
- Multiple selector fallbacks
- Schema validation with try-catch
- Partial data recovery strategies

### 3. Configuration Errors
- Environment variable validation
- Default value fallbacks
- Clear error messages with guidance

## Performance Considerations

### 1. Async Processing
- Concurrent page fetching
- Non-blocking I/O operations
- Efficient memory usage

### 2. Rate Limiting
- Respectful crawling intervals
- Configurable delays between requests
- User agent rotation

### 3. Memory Management
- Streaming data processing
- Efficient HTML parsing
- Garbage collection optimization

## Security Considerations

### 1. Data Privacy
- No credential storage in code
- Environment variable management
- Secure API key handling

### 2. Request Security
- Proper user agents
- Request header management
- IP rotation considerations

### 3. Input Validation
- URL validation
- Parameter sanitization
- SQL injection prevention (future database integration)

## Scalability Architecture

### Current Limitations
- Single-threaded processing per job board
- File-based storage only
- No distributed processing

### Future Enhancements
- Multi-board scraping capabilities
- Database integration for persistence
- Distributed processing with message queues
- API layer for external access

## Integration Points

### Current Integrations
- **SEEK.com.au**: Primary job board target
- **Crawl4AI**: Scraping framework
- **OpenAI**: Optional AI features (configured but not implemented)

### Future Integration Points
- **Additional Job Boards**: LinkedIn, Indeed, Glassdoor
- **Database Systems**: SQLite, PostgreSQL
- **API Frameworks**: FastAPI, Flask
- **Monitoring Systems**: Logging, metrics, alerting

## Deployment Architecture

### Development Environment
- Python 3.13+ virtual environment
- Local file system storage
- Console-based execution

### Production Considerations
- Docker containerization
- Scheduled execution (cron/airflow)
- Monitoring and logging infrastructure
- Error recovery mechanisms

## Technical Debt and Refactoring Opportunities

### Immediate Improvements
- Abstract scraper interface for multi-board support
- Configuration validation improvements
- Enhanced error logging and monitoring

### Medium-term Enhancements
- Database integration and data persistence
- API layer development
- Testing framework implementation

### Long-term Architecture
- Microservices separation
- Event-driven architecture
- Real-time processing capabilities