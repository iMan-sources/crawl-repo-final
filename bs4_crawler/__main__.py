import logging
import sys
from pathlib import Path
from .crawler import GitHubCrawler
from .config import LOGS_DIR
import time

def setup_logging():
    """Setup logging configuration"""
    log_file = LOGS_DIR / f"crawler_{time.strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting GitHub repository crawler...")
        crawler = GitHubCrawler()
        repos = crawler.run()
        logger.info(f"Successfully crawled {len(repos)} repositories")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Crawler stopped by user")
        return 1
        
    except Exception as e:
        logger.error(f"Crawler failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 