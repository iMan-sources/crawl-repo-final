import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Any
from tqdm import tqdm
import pandas as pd
import requests

from .config import (
    BASE_URL, NUM_WORKERS, MAX_REPOS,
    RESULTS_FILE, CSV_FILE, DB_CONFIG
)
from .repo_parser import RepoParser
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class GitHubCrawler:
    def __init__(self):
        """Initialize the crawler"""
        self.page_finder = PageFinder()
        
    def _worker_task(self, page: int) -> List[Dict]:
        """Process a single page
        
        Args:
            page (int): Page number to process
            
        Returns:
            List[Dict]: List of repository data
        """
        try:
            url = f"{BASE_URL}?page={page}"
            # retry
            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == 2:
                        logger.error(f"Failed after retries: {url}")
                        return []
                    time.sleep(2)
            
            # Parse repositories from page
            repos = RepoParser.parse_page(response.text)
            
            # Save to database
            db = DatabaseManager(**DB_CONFIG)  # Create new connection for each worker
            try:
                for repo in repos:
                    # Add full_name field if not present
                    if 'full_name' not in repo and 'user' in repo and 'name' in repo:
                        repo['full_name'] = f"{repo['user']}/{repo['name']}"
                    
                    db.insert_repository(repo)
            finally:
                db.close()  # Ensure connection is closed
            
            return repos
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {str(e)}")
            return []
        
    def run(self) -> list[Any] :
        """Run the crawler
        
        Returns:
            List[Dict]: List of crawled repository data
        """
        try:
            logger.info("Finding target page using binary search...")
            target_page, first_rank, last_rank = self.page_finder.find_target_page()
            
            if target_page == -1:
                logger.error("Could not find target page")
                return []
            
            logger.info(f"Found target page {target_page}. Now crawling all pages from 1 to 50...")
            
            # Create a list of all pages to crawl (1 to 50)
            all_repos = []
            pages_to_crawl = list(range(1, 51))

            with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
                future_to_page = {executor.submit(self._worker_task, page): page for page in pages_to_crawl}
                with tqdm(total=len(pages_to_crawl), desc="Processing pages") as pbar:
                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            result = future.result()
                            all_repos.extend(result)
                        except Exception as e:
                            logger.error(f"Error on page {page}: {e}")
                        pbar.update()
                all_repos.sort(key=lambda x: x['rank'])
                return all_repos

        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
            return []

class PageFinder:
    def __init__(self):
        """Initialize the page finder"""
        self.session = requests.Session()
        
    def _get_rank_range(self, page: int) -> tuple[int, int]:
        """Get the rank range for a page
        
        Args:
            page (int): Page number
            
        Returns:
            tuple[int, int]: First and last rank on the page
        """
        try:
            url = f"{BASE_URL}?page={page}"
            response = self.session.get(url)
            response.raise_for_status()
            
            repos = RepoParser.parse_page(response.text)
            if not repos:
                return -1, -1
            
            return repos[0]['rank'], repos[-1]['rank']
            
        except Exception as e:
            logger.error(f"Error getting rank range for page {page}: {str(e)}")
            return -1, -1
        
    def find_target_page(self) -> tuple[int, int, int]:
        """Find the page containing repositories around rank 5000
        
        Returns:
            tuple[int, int, int]: Page number, first rank, and last rank
        """
        left, right = 1, 200  # Reasonable page range
        target_rank = MAX_REPOS
        best_page = -1
        best_first_rank = -1
        best_last_rank = -1
        
        while left <= right:
            mid = (left + right) // 2
            first_rank, last_rank = self._get_rank_range(mid)
            
            if first_rank == -1:
                right = mid - 1
                continue
            
            logger.debug(f"Page {mid}: ranks {first_rank} to {last_rank}")
            
            if first_rank <= target_rank <= last_rank:
                best_page = mid
                best_first_rank = first_rank
                best_last_rank = last_rank
                break
            elif target_rank < first_rank:
                right = mid - 1
            else:
                left = mid + 1
        
        return best_page, best_first_rank, best_last_rank 