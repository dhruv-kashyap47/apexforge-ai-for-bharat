"""Database connection and management module."""
import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not provided. Set it in environment or .env file.")

        self.engine: Optional[Engine] = None
        self._connect()

    def _connect(self):
        """Create database engine."""
        try:
            self.engine = create_engine(self.database_url, pool_pre_ping=True)
            logger.info("Database connection established successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        if not self.engine:
            self._connect()

        conn = self.engine.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a query and return results as list of dictionaries."""
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def execute_command(self, command: str, params: Optional[Dict] = None) -> int:
        """Execute a command (INSERT, UPDATE, DELETE) and return affected rows."""
        with self.get_connection() as conn:
            result = conn.execute(text(command), params or {})
            return result.rowcount

    def insert_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append'):
        """Insert a pandas DataFrame into a database table."""
        try:
            df.to_sql(table_name, self.engine, if_exists=if_exists, index=False, method='multi')
            logger.info(f"Inserted {len(df)} rows into {table_name}")
            return len(df)
        except SQLAlchemyError as e:
            logger.error(f"Failed to insert data into {table_name}: {e}")
            raise

    def read_dataframe(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute a query and return results as a pandas DataFrame."""
        try:
            with self.get_connection() as conn:
                # Use SQLAlchemy text() for proper parameter binding
                from sqlalchemy import text
                result = pd.read_sql(text(query), conn, params=params)
                return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to read data: {e}")
            raise

    def initialize_schema(self, schema_file: str = 'schema.sql'):
        """Initialize database schema from SQL file."""
        try:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            with self.get_connection() as conn:
                conn.execute(text(schema_sql))
            logger.info("Database schema initialized successfully")
        except FileNotFoundError:
            logger.error(f"Schema file {schema_file} not found")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        queries = {
            'total_raw_records': 'SELECT COUNT(*) as count FROM raw_records',
            'total_ubids': 'SELECT COUNT(*) as count FROM ubid_registry',
            'total_matched_groups': 'SELECT COUNT(*) as count FROM matched_groups',
            'pending_reviews': 'SELECT COUNT(*) as count FROM review_queue WHERE status = :status',
            'active_businesses': "SELECT COUNT(*) as count FROM ubid_registry WHERE business_status = 'Active'",
            'dormant_businesses': "SELECT COUNT(*) as count FROM ubid_registry WHERE business_status = 'Dormant'",
            'closed_businesses': "SELECT COUNT(*) as count FROM ubid_registry WHERE business_status = 'Closed'",
        }

        stats = {}
        for key, query in queries.items():
            result = self.execute_query(query, {'status': 'Pending'} if 'pending' in key else {})
            stats[key] = result[0]['count'] if result else 0

        return stats

    def get_next_sequence_number(self, state_code: str, district_code: str, category: str) -> int:
        """Get the next sequence number for UBID generation."""
        query = """
            SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
            FROM ubid_registry
            WHERE state_code = :state_code AND district_code = :district_code AND category = :category
        """
        result = self.execute_query(query, {
            'state_code': state_code,
            'district_code': district_code,
            'category': category
        })
        return result[0]['next_seq'] if result else 1


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def reset_db_manager():
    """Reset the global database manager (useful for testing)."""
    global _db_manager
    _db_manager = None
