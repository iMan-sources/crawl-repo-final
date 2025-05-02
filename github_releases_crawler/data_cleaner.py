import re
import html
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataCleaner:
    @staticmethod
    def clean_release_content(content: str) -> str:
        """Clean and sanitize release content
        
        Args:
            content (str): Raw release content
            
        Returns:
            str: Cleaned content
        """
        if not content:
            return ""
            
        try:
            # Remove HTML tags while preserving important content
            content = re.sub(r'<details.*?>(.*?)</details>', r'\1', content, flags=re.DOTALL)
            content = re.sub(r'<summary.*?>(.*?)</summary>', r'\1', content, flags=re.DOTALL)
            
            # Convert HTML entities
            content = html.unescape(content)
            
            # Remove problematic characters
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
            
            # Normalize newlines
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Trim excessive whitespace
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            content = content.strip()
            
            # Truncate if too long (MySQL TEXT limit is 65,535 bytes)
            max_length = 65000  # Leave some margin
            if len(content.encode('utf-8')) > max_length:
                # Try to truncate at a sentence or line boundary
                content = content.encode('utf-8')[:max_length].decode('utf-8', 'ignore')
                # Find last sentence or line ending
                last_break = max(
                    content.rfind('.'),
                    content.rfind('\n'),
                    content.rfind('!'),
                    content.rfind('?')
                )
                if last_break > max_length * 0.8:  # Only truncate at break if reasonably close to end
                    content = content[:last_break + 1]
                content = content.strip()
                content += "\n[Content truncated due to length]"
            
            return content
            
        except Exception as e:
            logger.error(f"Error cleaning content: {str(e)}")
            return ""
    
    @staticmethod
    def clean_repository_data(repo_data: Dict) -> Dict:
        """Clean repository data
        
        Args:
            repo_data (Dict): Raw repository data
            
        Returns:
            Dict: Cleaned repository data
        """
        if not isinstance(repo_data, dict):
            return {}
            
        try:
            cleaned = {}
            
            # Clean text fields
            text_fields = ['user', 'name', 'full_name', 'description', 'language']
            for field in text_fields:
                if field in repo_data:
                    value = str(repo_data[field] or '')
                    # Remove problematic characters
                    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
                    # Normalize whitespace
                    value = ' '.join(value.split())
                    cleaned[field] = value[:255] if field != 'description' else value
            
            # Clean URL fields
            url_fields = ['avatar_url', 'repo_url']
            for field in url_fields:
                if field in repo_data:
                    value = str(repo_data[field] or '')
                    # Basic URL validation
                    if re.match(r'^https?://', value):
                        cleaned[field] = value[:2048]  # Reasonable URL length limit
                    else:
                        cleaned[field] = None
            
            # Clean numeric fields
            numeric_fields = ['rank', 'stars']
            for field in numeric_fields:
                if field in repo_data:
                    try:
                        cleaned[field] = int(repo_data[field])
                    except (TypeError, ValueError):
                        cleaned[field] = None
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning repository data: {str(e)}")
            return {}
    
    @staticmethod
    def clean_release_data(release: Dict) -> Optional[Dict]:
        """Clean release data
        
        Args:
            release (Dict): Raw release data
            
        Returns:
            Optional[Dict]: Cleaned release data or None if invalid
        """
        if not isinstance(release, dict):
            return None
            
        try:
            # Validate and clean release ID
            try:
                release_id = int(release.get('id'))
                if release_id <= 0:
                    return None
            except (TypeError, ValueError):
                return None
            
            # Clean content
            content = DataCleaner.clean_release_content(release.get('body', ''))
            if not content:
                return None
            
            # Get tag name
            tag_name = str(release.get('tag_name', '')).strip()
            
            return {
                'id': release_id,
                'tag_name': tag_name,
                'body': content
            }
            
        except Exception as e:
            logger.error(f"Error cleaning release data: {str(e)}")
            return None
    
    @staticmethod
    def clean_releases_batch(releases: List[Dict]) -> List[Dict]:
        """Clean a batch of releases
        
        Args:
            releases (List[Dict]): List of raw release data
            
        Returns:
            List[Dict]: List of cleaned release data
        """
        if not isinstance(releases, list):
            return []
            
        cleaned = []
        for release in releases:
            cleaned_release = DataCleaner.clean_release_data(release)
            if cleaned_release:
                cleaned.append(cleaned_release)
        
        return cleaned 