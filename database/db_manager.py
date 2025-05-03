import mysql.connector
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, host: str = 'localhost', user: str = 'root', password: str = 'abcde12345-', database: str = 'github_data'):
        """Initialize database connection
        
        Args:
            host (str): MySQL host
            user (str): MySQL user
            password (str): MySQL password
            database (str): Database name
        """
        self.connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.connection.cursor(dictionary=True)
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create repositories table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_full_name (full_name),
                    INDEX idx_rank (`rank`),
                    INDEX idx_stars (stars),
                    INDEX idx_language (language)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            # Create releases table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS releases (
                    id INTEGER NOT NULL,
                    tag_name VARCHAR(255),
                    content MEDIUMTEXT NOT NULL,
                    repo_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY (repo_id) REFERENCES repositories(id),
                    INDEX idx_repo_id (repo_id),
                    INDEX idx_tag_name (tag_name)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            # Create commits table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    hash VARCHAR(40) NOT NULL,
                    message TEXT NOT NULL,
                    releaseID INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (hash),
                    FOREIGN KEY (releaseID) REFERENCES repositories(id),
                    INDEX idx_release_id (releaseID)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)

            self.connection.commit()
            logger.info("Database tables created successfully")

        except mysql.connector.Error as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise

    def insert_repository(self, repo_data: Dict) -> Optional[int]:
        """Insert repository data and return its ID
        
        Args:
            repo_data (Dict): Repository data
            
        Returns:
            Optional[int]: Repository ID if successful, None otherwise
        """
        try:
            # Split full_name into user and name if not already split
            if 'user' not in repo_data or 'name' not in repo_data:
                user, name = repo_data['full_name'].split('/')
                repo_data['user'] = user
                repo_data['name'] = name

            query = """
                INSERT INTO repositories 
                (user, name, full_name, `rank`, stars, description, language, avatar_url, repo_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                `rank` = VALUES(`rank`),
                stars = VALUES(stars),
                description = VALUES(description),
                language = VALUES(language),
                avatar_url = VALUES(avatar_url),
                repo_url = VALUES(repo_url)
            """
            values = (
                repo_data['user'],
                repo_data['name'],
                repo_data['full_name'],
                repo_data.get('rank'),
                repo_data.get('stars'),
                repo_data.get('description'),
                repo_data.get('language'),
                repo_data.get('avatar_url'),
                repo_data.get('repo_url')
            )

            self.cursor.execute(query, values)
            self.connection.commit()

            # If this was an update, get the existing ID
            if self.cursor.lastrowid == 0:
                self.cursor.execute(
                    "SELECT id FROM repositories WHERE full_name = %s",
                    (repo_data['full_name'],)
                )
                result = self.cursor.fetchone()
                return result['id'] if result else None

            return self.cursor.lastrowid

        except mysql.connector.Error as e:
            logger.error(f"Error inserting repository {repo_data.get('full_name')}: {str(e)}")
            self.connection.rollback()
            return None

    def insert_releases(self, releases: List[Dict], repo_id: int) -> bool:
        """Insert releases for a repository
        
        Args:
            releases (List[Dict]): List of release data
            repo_id (int): Repository ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not releases:
                return True

            query = """
                INSERT INTO releases (id, tag_name, content, repo_id)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    tag_name = VALUES(tag_name),
                    content = VALUES(content)
            """

            values = [
                (release['id'], release.get('tag_name'), release['body'], repo_id)
                for release in releases
            ]

            self.cursor.executemany(query, values)
            self.connection.commit()
            return True

        except mysql.connector.Error as e:
            logger.error(f"Error inserting releases for repository {repo_id}: {str(e)}")
            self.connection.rollback()
            return False

    def get_repository_id(self, full_name: str) -> Optional[int]:
        """Get repository ID by full name
        
        Args:
            full_name (str): Repository full name (user/name)
            
        Returns:
            Optional[int]: Repository ID if found, None otherwise
        """
        try:
            query = "SELECT id FROM repositories WHERE full_name = %s"
            self.cursor.execute(query, (full_name,))
            result = self.cursor.fetchone()
            return result['id'] if result else None

        except mysql.connector.Error as e:
            logger.error(f"Error getting repository ID for {full_name}: {str(e)}")
            return None

    def get_all_repositories(self) -> List[Dict]:
        """Get all repositories
        
        Returns:
            List[Dict]: List of repository data
        """
        try:
            query = "SELECT * FROM repositories"
            self.cursor.execute(query)
            return self.cursor.fetchall()

        except mysql.connector.Error as e:
            logger.error(f"Error getting repositories: {str(e)}")
            return []

    def insert_commits(self, commits: List[Dict], repo_id: int) -> bool:
        """Insert commits for a repository
        
        Args:
            commits (List[Dict]): List of commit data
            repo_id (int): Repository ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not commits:
                return True

            query = """
                INSERT INTO commits (hash, message, releaseID)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE message = VALUES(message)
            """

            values = [
                (commit['hash'], commit['message'], repo_id)
                for commit in commits
            ]

            self.cursor.executemany(query, values)
            self.connection.commit()
            return True

        except mysql.connector.Error as e:
            logger.error(f"Error inserting commits for repository {repo_id}: {str(e)}")
            self.connection.rollback()
            return False

    def close(self):
        """Close database connection"""
        try:
            self.cursor.close()
            self.connection.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")