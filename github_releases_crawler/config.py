import os
from pathlib import Path

# Base configuration
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'output'
LOGS_DIR = BASE_DIR / 'logs'

# Ensure directories exist
for directory in [OUTPUT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# GitHub API settings
GITHUB_API_BASE = 'https://api.github.com'
GITHUB_TOKEN = ''
MAX_REPOS = 5000
NUM_WORKERS = 4
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2

# Batch processing settings
BATCH_SIZE = 10  # Number of repos to process in each batch

# Rate limiting settings
RATE_LIMIT_RESERVE = 100  # Keep some requests in reserve
MIN_RATE_LIMIT = 10  # Pause if rate limit gets this low

# Input/Output files
INPUT_REPOS_FILE = str(Path('/Users/levietanh/Desktop/Git-workplace/crawl-repo/bs4_crawler/output/github_repos.json'))
RESULTS_FILE = OUTPUT_DIR / 'github_releases.json'

# Database settings
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'abcde12345-',  # Set your MySQL password here
    'database': 'github_data'
}

# Request headers
HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f'token {GITHUB_TOKEN}',
    'User-Agent': 'GitHub-Release-Crawler'
} 