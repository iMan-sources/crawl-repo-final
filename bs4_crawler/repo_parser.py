from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import logging
import re

from .config import BASE_URL

logger = logging.getLogger(__name__)

class RepoParser:
    @staticmethod
    def _extract_repo_info_from_url(repo_url: str) -> Tuple[str, str, str]:
        """Extract repository user and name from URL
        
        Args:
            repo_url (str): Repository URL
            
        Returns:
            Tuple[str, str, str]: (full_name, user, repo_name)
            where full_name is in format "user/repo"
        """
        # Parse the URL path which is in format "/user/repo"
        path = urlparse(repo_url).path.strip('/')
        try:
            user, repo_name = path.split('/')
            return f"{user}/{repo_name}", user, repo_name
        except ValueError:
            # If we can't split into user/repo, return the whole path as name
            return path, "", path

    @staticmethod
    def parse_repository(item_html: str) -> Optional[Dict]:
        """Parse a single repository item from its HTML
        
        Args:
            item_html (str): HTML content of the repository item
            
        Returns:
            Optional[Dict]: Repository data if successfully parsed, None otherwise
        """
        try:
            soup = BeautifulSoup(item_html, 'html.parser')
            
            # Extract rank
            name_container = soup.select_one('.name')
            if not name_container:
                logger.warning("No name container found")
                return None
            
            # Extract rank from the first text node
            rank_text = next((text.strip() for text in name_container.stripped_strings), None)
            if not rank_text:
                logger.warning("No rank text found")
                return None
            
            rank_match = re.match(r'^(\d+)\.', rank_text)
            if not rank_match:
                logger.warning(f"Could not parse rank from: {rank_text}")
                return None
            rank = int(rank_match.group(1))
            
            # Extract repo URL and name from it
            repo_url = None
            link = soup.select_one('a')
            if link and 'href' in link.attrs:
                repo_url = urljoin(BASE_URL, link['href'])
                full_name, user, name = RepoParser._extract_repo_info_from_url(repo_url)
            else:
                logger.warning(f"No valid URL found for repository rank {rank}")
                return None
            
            # Extract stars
            stars_elems = soup.select('.stargazers_count')
            if stars_elems:
                # Get the last text node which contains the star count
                stars_text = stars_elems[-1].get_text(strip=True)
                try:
                    stars = int(stars_text.replace(',', ''))
                except ValueError:
                    logger.warning(f"Could not parse stars from: {stars_text}")
                    stars = 0
            else:
                stars = 0
            
            # Extract description
            desc_elem = soup.select_one('.repo-description')
            description = desc_elem.get('title', '') if desc_elem else None
            if not description:
                description = desc_elem.get_text(strip=True) if desc_elem else "No description available"
            
            # Extract language
            lang_elem = soup.select_one('.repo-language span')
            language = lang_elem.get_text(strip=True) if lang_elem else "No language available"
            
            # Extract avatar URL
            avatar_url = None
            # Try multiple selectors
            for selector in ['img.avatar_image_big', '.avatar_image_big img', '.list-group-item img']:
                img = soup.select_one(selector)
                if img and 'src' in img.attrs:
                    avatar_url = img['src']
                    break
            
            return {
                'rank': rank,
                'user': user,
                'name': name,
                'full_name': full_name,
                'stars': stars,
                'description': description,
                'language': language,
                'avatar_url': avatar_url,
                'repo_url': repo_url
            }
            
        except Exception as e:
            logger.error(f"Error parsing repository: {str(e)}")
            return None
    
    @classmethod
    def parse_page(cls, html: str) -> List[Dict]:
        """Parse all repositories from a page
        
        Args:
            html (str): HTML content of the page
            
        Returns:
            List[Dict]: List of parsed repository data
        """
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.list-group-item.paginated_item')
        
        repos = []
        for item in items:
            repo_data = cls.parse_repository(str(item))
            if repo_data:
                repos.append(repo_data)
        
        return repos 