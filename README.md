# GitHub Repository Crawler

This project consists of two main components:

1. GitStar Ranking Crawler (BS4-based)
2. GitHub Releases Crawler

Both components now support MySQL database storage in addition to JSON/CSV output.

## Database Schema

The project uses MySQL to store repository and release data:

```sql
-- Repositories table
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    `rank` INTEGER,
    stars INTEGER,
    description TEXT,
    language VARCHAR(100),
    avatar_url TEXT,
    repo_url TEXT,
    UNIQUE KEY unique_full_name (full_name)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Releases table
CREATE TABLE releases (
    id INTEGER NOT NULL,
    content TEXT NOT NULL,
    repo_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 1. GitStar Ranking Crawler

Located in `bs4_crawler/`, this component crawls repository data from gitstar-ranking.com:

- Uses BeautifulSoup4 for HTML parsing
- Implements binary search to find specific repository ranks
- Uses parallel processing with worker pools
- Stores data in both MySQL database and JSON/CSV formats
- Collects repository metadata: rank, name, stars, description, language, etc.

## 2. GitHub Releases Crawler

Located in `github_releases_crawler/`, this component fetches release information from GitHub's API:

### Features

- Fetches releases for repositories using GitHub's REST API
- Processes repositories in parallel using multiple workers
- Implements rate limiting and error handling
- Saves data incrementally to MySQL database and JSON file
- Extracts only essential release data (id and body fields)
- Maintains referential integrity with repositories table

### Configuration

```python
# GitHub API settings
MAX_REPOS = 5000          # Maximum repositories to process
NUM_WORKERS = 4           # Number of parallel workers
BATCH_SIZE = 10          # Repositories per batch
REQUEST_TIMEOUT = 30     # API request timeout
MAX_RETRIES = 3         # Number of retries for failed requests

# Database settings
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'github_crawler'
}
```

### Error Handling

The crawler handles various scenarios:

- API Response Issues:

  - 404: Repository or releases not found
  - 451: Repository unavailable for legal reasons
  - 401/403: Authentication errors
  - Rate limit exceeded
  - Network timeouts and connection errors

- Database Issues:
  - Connection errors
  - Duplicate entries
  - Foreign key constraints
  - Transaction management

### Data Storage

The project now supports dual storage:

1. Database Storage (Primary):

   - MySQL database with proper schema
   - Foreign key relationships
   - Transaction support
   - Concurrent access handling

2. File Storage (Secondary):
   - JSON files for compatibility
   - CSV export for analysis
   - Serves as backup

### Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up MySQL database:

```sql
CREATE DATABASE github_crawler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. Configure database connection in both crawlers' config files:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'github_crawler'
}
```

4. Set GitHub API token in `github_releases_crawler/config.py`:

```python
GITHUB_TOKEN = 'your_github_token'
```

5. Run the crawlers:

```bash
# First crawl repositories
python run_bs4.py

# Then crawl releases
python run_releases.py
```

### Implementation Details

1. **Database Manager**

   - Handles all database operations
   - Implements connection pooling
   - Manages transactions and rollbacks
   - Handles concurrent access

   ```python
   class DatabaseManager:
       def insert_repository(self, repo_data: Dict) -> Optional[int]
       def insert_releases(self, releases: List[Dict], repo_id: int) -> bool
       def get_repository_id(self, full_name: str) -> Optional[int]
   ```

2. **Worker Pool**

   - Each worker has its own database connection
   - Implements parallel processing using `multiprocessing`
   - Uses connection pooling for efficiency
   - Handles database transaction isolation

3. **Data Consistency**

   - Atomic transactions for data integrity
   - Foreign key constraints for referential integrity
   - Unique constraints to prevent duplicates
   - Proper error handling and rollbacks

4. **Performance Optimization**
   - Batch inserts for better performance
   - Connection pooling to reduce overhead
   - Indexed queries for faster lookups
   - Efficient data types and constraints

### Project Structure

```
.
├── bs4_crawler/                 # GitStar ranking crawler
│   ├── output/
│   │   └── github_repos.json   # Repository list
│   └── ...
├── github_releases_crawler/     # GitHub releases crawler
│   ├── config.py               # Configuration settings
│   ├── crawler.py              # Main crawler implementation
│   ├── __init__.py
│   ├── __main__.py            # Entry point
│   ├── output/
│   │   └── github_releases.json # Release data
│   └── logs/                   # Crawler logs
└── run_releases.py             # Runner script
```

## Dependencies

- requests: HTTP client for API calls
- tqdm: Progress bar visualization
- retry: Automatic retry mechanism
- multiprocessing: Parallel processing support

## Architecture

### Overview

The GitHub Releases Crawler follows a multi-layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│                  Runner (run_releases.py)           │
└───────────────────────────┬─────────────────────────┘
                           │
┌───────────────────────────┴─────────────────────────┐
│              Crawler (GitHubReleasesCrawler)        │
├─────────────────┬──────────────────┬────────────────┤
│  API Client     │   Worker Pool    │  Data Manager  │
└─────────┬───────┴──────────┬───────┴────────┬───────┘
          │                  │                │
┌─────────┴───────┐  ┌──────┴───────┐ ┌──────┴───────┐
│  Rate Limiter   │  │ Process Queue │ │ File Storage │
└─────────────────┘  └──────────────┘ └──────────────┘
```

### Components

1. **Runner Layer**

   - Entry point of the application
   - Initializes logging and crawler instance
   - Handles top-level exception management
   - File: `run_releases.py`

2. **Crawler Layer (Core)**

   - Main orchestrator class `GitHubReleasesCrawler`
   - Manages the overall crawling process
   - Coordinates between components
   - Implements batch processing logic
   - File: `crawler.py`

3. **API Client Component**

   - Handles GitHub API communication
   - Implements retry mechanism with exponential backoff
   - Manages session and authentication
   - Error handling and response processing

   ```python
   @retry(tries=MAX_RETRIES, delay=RETRY_DELAY, backoff=2)
   def _fetch_releases(self, repo: Dict) -> Optional[List[Dict]]
   ```

4. **Worker Pool Component**

   - Implements parallel processing using `multiprocessing`
   - Distributes work among worker processes
   - Uses Queue for inter-process communication
   - Manages worker lifecycle

   ```python
   def _worker_process(self, worker_id: int, repos: List[Dict], result_queue: Queue)
   def _process_batch(self, batch: List[Dict]) -> List[Dict]
   ```

5. **Data Manager Component**
   - Handles data persistence
   - Implements incremental saving
   - Manages file I/O operations
   ```python
   def _load_existing_releases(self) -> List[Dict]
   def _save_releases(self, releases: List[Dict])
   ```

### Design Patterns Used

1. **Factory Pattern**

   - Used in worker process creation
   - Standardizes worker initialization

2. **Observer Pattern**

   - Progress reporting using `tqdm`
   - Event-based logging system

3. **Strategy Pattern**

   - Configurable retry mechanism
   - Flexible rate limiting strategy

4. **Producer-Consumer Pattern**
   - Workers (producers) generate release data
   - Main process (consumer) collects and saves results

### Data Flow

1. **Input Processing**

   ```
   Load Repositories → Split into Batches → Distribute to Workers
   ```

2. **Worker Processing**

   ```
   Fetch Releases → Extract Fields → Queue Results
   ```

3. **Data Collection**
   ```
   Collect from Queue → Merge Results → Save to File
   ```

### Error Handling Strategy

1. **Hierarchical Error Management**

   - Worker-level error handling
   - Batch-level recovery
   - Global exception handling

2. **Graceful Degradation**
   - Continues processing on non-critical errors
   - Skips problematic repositories
   - Maintains data consistency

### Performance Optimizations

1. **Batch Processing**

   - Reduces memory usage
   - Enables incremental saving
   - Prevents data loss

2. **Parallel Processing**

   - Multiple workers for better throughput
   - Efficient resource utilization
   - Configurable worker count

3. **Rate Limiting**
   - Proactive rate limit monitoring
   - Automatic backoff when needed
   - Reserve maintenance for critical operations
