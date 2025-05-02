import logging
import sys
from pathlib import Path
from .crawler import GitHubReleasesCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    try:
        logger.info("Starting GitHub releases crawler...")
        
        # Create and run crawler
        crawler = GitHubReleasesCrawler()
        results = crawler.run()
        
        if results is None:
            results = []
        
        logger.info(f"Successfully crawled releases for {len(results)} repositories")
        
    except Exception as e:
        logger.error(f"Crawler failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 