# BS4 GitHub Repository Crawler

A high-performance web crawler for extracting GitHub repository data from gitstar-ranking.com using BeautifulSoup4, with support for parallel processing.

## Architecture Overview

The crawler follows a multi-stage pipeline architecture with parallel processing:

```ascii
                                     ┌──────────────┐
                                     │   Config     │
                                     │  (settings)  │
                                     └──────┬───────┘
                                           │
                                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PageFinder  │    │ GitHubCrawler│    │ Worker Pool  │
│(binary search│◄───│   (main)     │───►│(process data)│
│ & fetch)     │    │              │    │             │
└──────┬───────┘    └──────────────┘    └──────┬──────┘
       │                                        │
       ▼                                       ▼
┌──────────────┐                        ┌──────────────┐
│ HTML Content │                        │ RepoParser   │
│  Processing  │                        │(parse HTML)  │
└──────────────┘                        └──────┬───────┘
                                              │
                                              ▼
                                     ┌──────────────┐
                                     │ JSON & CSV   │
                                     │   Output     │
                                     └──────────────┘
```

## Workflow Steps

1. **Initialization & Configuration**

   ```ascii
   ┌─────────────┐
   │ Start       │
   └─────┬───────┘
         ▼
   ┌─────────────┐
   │ Load Config │
   └─────────────┘
   ```

2. **Binary Search & Page Discovery**

   ```ascii
   ┌─────────────┐     ┌─────────────┐
   │Find Target  │     │Verify Page  │
   │   Page     │────►│   Range     │
   └─────────────┘     └─────────────┘
   ```

3. **Parallel Processing**

   ```ascii
   ┌─────────────┐     ┌─────────────┐
   │ Split Pages │     │Worker Pool  │
   │Among Workers│────►│(4 Workers)  │
   └─────────────┘     └──────┬──────┘
                              │
                        ┌─────┴──────┐
                        ▼     ▼      ▼
                     Worker Worker Worker
                        1     2      3
   ```

4. **Data Extraction & Storage**

   ```ascii
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │Parse Repo   │     │Merge Worker │     │Save to JSON │
   │   Data      │────►│  Results    │────►│   & CSV     │
   └─────────────┘     └─────────────┘     └─────────────┘
   ```

## Components

### 1. GitHubCrawler (crawler.py)

- Main orchestrator class
- Manages the overall crawling process
- Coordinates workers and data aggregation

### 2. PageFinder (page_finder.py)

- Uses binary search to find target page
- Handles page fetching with retries
- Validates page ranges

### 3. RepoParser (repo_parser.py)

- Parses HTML content
- Extracts repository information
- Handles various HTML structures

### 4. Configuration (config.py)

- Centralizes crawler settings
- Configures workers and paths
- Sets request timeouts and retries

## Features

- **Binary Search**: Efficiently finds target page
- **Parallel Processing**: Uses Python's multiprocessing for parallel page processing
- **Robust Parsing**: Multiple strategies for data extraction
- **Error Handling**: Comprehensive retry and error recovery
- **Progress Tracking**: Real-time progress monitoring
- **Multiple Outputs**: Both JSON and CSV output formats

## Performance Optimizations

1. **Binary Search Strategy**

   ```ascii
   Start ──► Check Mid Page ──┬─► Found Target ──► Process All Pages
                              │
                              └─► Adjust Range ──► Repeat
   ```

2. **Worker Distribution**
   ```ascii
   Pages: [1..50] ──► Split ──┬─► Worker 1: [1..12]
                              ├─► Worker 2: [13..25]
                              ├─► Worker 3: [26..37]
                              └─► Worker 4: [38..50]
   ```

## Error Handling

- Retries for network failures
- Graceful degradation for parsing errors
- Comprehensive logging

## Output Format

```json
{
  "rank": 1,
  "name": "owner/repo",
  "stars": 50000,
  "description": "Repository description",
  "language": "Python",
  "avatar_url": "https://...",
  "repo_url": "https://..."
}
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run the crawler
python -m bs4_crawler

# Output files will be in:
# - bs4_crawler/output/github_repos.json
# - bs4_crawler/output/github_repos.csv
```
