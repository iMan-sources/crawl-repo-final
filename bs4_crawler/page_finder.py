import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Tuple
from fake_useragent import UserAgent
from retry import retry

from .config import (
    BASE_URL, MAX_REPOS,
    MAX_RETRIES, RETRY_DELAY, REQUEST_TIMEOUT,
    TARGET_REPO_RANK
)

logger = logging.getLogger(__name__)

class PageFinder:
    def __init__(self):
        """Initialize page finder"""
        self.session = requests.Session()
    
    @retry(tries=MAX_RETRIES, delay=RETRY_DELAY, backoff=2)
    def _fetch_page(self, page: int) -> str:
        """Fetch page content with retries
        
        Args:
            page (int): Page number to fetch
            
        Returns:
            str: HTML content of the page
        """
        url = f"{BASE_URL}?page={page}"
        
        headers = {
            'User-Agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    
    def _get_first_rank_on_page(self, html: str) -> int:
        """Get the rank of the first repository on the page
        
        Args:
            html (str): HTML content of the page
            
        Returns:
            int: Rank of the first repository
        """
        soup = BeautifulSoup(html, 'html.parser')
        first_repo = soup.select_one('.list-group-item.paginated_item')
        if not first_repo:
            return -1
        
        # Extract rank from the name span
        name_span = first_repo.select_one('.name')
        if not name_span:
            return -1
            
        # The rank is the first text node in the name span
        rank_text = next((text.strip() for text in name_span.stripped_strings), None)
        if not rank_text:
            return -1
            
        try:
            # Remove the trailing dot from rank (e.g., "1." -> "1")
            return int(rank_text.rstrip('.'))
        except (ValueError, AttributeError):
            return -1
    
    def _get_last_rank_on_page(self, html: str) -> int:
        """Get the rank of the last repository on the page
        
        Args:
            html (str): HTML content of the page
            
        Returns:
            int: Rank of the last repository
        """
        soup = BeautifulSoup(html, 'html.parser')
        repos = soup.select('.list-group-item.paginated_item')
        if not repos:
            return -1
        
        # Get the last repository's name span
        name_span = repos[-1].select_one('.name')
        if not name_span:
            return -1
            
        # The rank is the first text node in the name span
        rank_text = next((text.strip() for text in name_span.stripped_strings), None)
        if not rank_text:
            return -1
            
        try:
            # Remove the trailing dot from rank (e.g., "100." -> "100")
            return int(rank_text.rstrip('.'))
        except (ValueError, AttributeError):
            return -1

    def find_target_page(self) -> Tuple[int, int, int]:
        """Use binary search to find the page containing the target rank
        
        Returns:
            Tuple[int, int, int]: (page_number, first_rank, last_rank)
        """
        left = 1
        right = 100  # Maximum page number on gitstar-ranking.com
        target_page = -1
        first_rank = -1
        last_rank = -1
        
        logger.info(f"Starting binary search for repository rank {TARGET_REPO_RANK}")
        
        while left <= right:
            mid = (left + right) // 2
            try:
                html = self._fetch_page(mid)
                page_first_rank = self._get_first_rank_on_page(html)
                page_last_rank = self._get_last_rank_on_page(html)
                
                if page_first_rank == -1 or page_last_rank == -1:
                    # Page is empty or invalid, try lower page
                    right = mid - 1
                    continue
                
                logger.info(f"Page {mid}: First rank={page_first_rank}, Last rank={page_last_rank}")
                
                if page_first_rank <= TARGET_REPO_RANK <= page_last_rank:
                    # Found the target page
                    target_page = mid
                    first_rank = page_first_rank
                    last_rank = page_last_rank
                    break
                elif TARGET_REPO_RANK < page_first_rank:
                    right = mid - 1
                else:
                    left = mid + 1
                    
            except Exception as e:
                logger.error(f"Error processing page {mid}: {str(e)}")
                right = mid - 1
        
        if target_page == -1:
            logger.warning("Could not find exact target page, using closest match")
            # Use the last valid page we found
            target_page = right
            html = self._fetch_page(target_page)
            first_rank = self._get_first_rank_on_page(html)
            last_rank = self._get_last_rank_on_page(html)
        
        logger.info(f"Found target page {target_page} with ranks {first_rank}-{last_rank}")
        return target_page, first_rank, last_rank 