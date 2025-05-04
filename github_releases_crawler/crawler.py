import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from multiprocessing import Pool
from tqdm import tqdm
import requests

from .config import (
    GITHUB_API_BASE, HEADERS, MAX_REPOS,
    NUM_WORKERS, REQUEST_TIMEOUT, MAX_RETRIES,
    RETRY_DELAY, INPUT_REPOS_FILE,
    RATE_LIMIT_RESERVE, MIN_RATE_LIMIT,
    BATCH_SIZE, DB_CONFIG
)
from database.db_manager import DatabaseManager
from .data_cleaner import DataCleaner

logger = logging.getLogger(__name__)

def process_repo(repo: Dict) -> Optional[Tuple[str, List[Dict]]]:
    """Process a single repository
    
    Args:
        repo (Dict): Repository data
        
    Returns:
        Optional[Tuple[str, List[Dict]]]: Tuple of (full_name, releases) if successful
    """
    try:
        # Create session for this repo
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Create database connection
        db = DatabaseManager(**DB_CONFIG)
        
        try:
            # Clean repository data first
            cleaned_repo = DataCleaner.clean_repository_data(repo)
            if not cleaned_repo:
                logger.warning(f"Invalid repository data for {repo.get('full_name', 'unknown')}")
                return None
            
            # First get repository ID
            repo_id = db.get_repository_id(cleaned_repo['full_name'])
            if repo_id is None:
                logger.warning(f"Repository {cleaned_repo['full_name']} not found in database")
                return None
            
            # Then fetch releases
            url = f"{GITHUB_API_BASE}/repos/{cleaned_repo['full_name']}/releases"
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            releases = response.json()
            if not isinstance(releases, list):
                logger.warning(f"Unexpected response format for {cleaned_repo['full_name']}")
                return None
            
            # Clean and validate releases
            cleaned_releases = DataCleaner.clean_releases_batch(releases)
            if cleaned_releases:
                if db.insert_releases(cleaned_releases, repo_id):
                    return cleaned_repo['full_name'], cleaned_releases
            
            # Check rate limit
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            if remaining < MIN_RATE_LIMIT:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(0, reset_time - time.time())
                if wait_time > 0:
                    logger.info(f"Rate limit low ({remaining}). Waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
            
            return None
            
        finally:
            db.close()
            session.close()
            
    except Exception as e:
        logger.error(f"Error processing {repo.get('full_name', 'unknown')}: {str(e)}")
        return None

class GitHubReleasesCrawler:
    def __init__(self):
        """Initialize the crawler"""
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._load_repos()

    def _load_repos(self):
        """Load repository data from JSON file"""
        try:
            db = DatabaseManager(**DB_CONFIG)
            try:
                self.repos = db.get_all_repositories()
                logger.info(f"Loaded {len(self.repos)} repositories from database")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error loading repositories from database: {str(e)}")
            self.repos = []

    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of repositories using multiple workers
        
        Args:
            batch (List[Dict]): List of repositories to process
            
        Returns:
            List[Dict]: List of results
        """
        results = []
        with Pool(processes=NUM_WORKERS) as pool:
            with tqdm(total=len(batch), desc="Processing repositories") as pbar:
                for result in pool.imap_unordered(process_repo, batch):
                    if result is not None:
                        results.append(result)
                    pbar.update()
        
        logger.info(f"Batch complete: processed {len(results)} repositories")
        return results
        
    def run(self) -> List[Dict]:
        """Run the crawler
        
        Returns:
            List[Dict]: List of results
        """
        try:
            if not self.repos:
                logger.error("No repositories loaded")
                return []
            
            # Clean repository data before processing
            self.repos = [
                repo for repo in map(DataCleaner.clean_repository_data, self.repos)
                if repo  # Filter out invalid repos
            ]
            
            # Limit to MAX_REPOS
            repos_to_process = self.repos[:MAX_REPOS]
            
            logger.info(f"Processing {len(repos_to_process)} repositories in batches of {BATCH_SIZE}...")
            
            # Process repositories in batches
            all_results = []
            for i in range(0, len(repos_to_process), BATCH_SIZE):
                batch = repos_to_process[i:i + BATCH_SIZE]
                logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(repos_to_process)-1)//BATCH_SIZE + 1}")
                
                results = self._process_batch(batch)
                all_results.extend(results)
                
                # Small delay between batches to avoid overwhelming the API
                time.sleep(1)
            
            logger.info(f"Completed processing {len(all_results)} repositories")
            return all_results
            
        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
            return []