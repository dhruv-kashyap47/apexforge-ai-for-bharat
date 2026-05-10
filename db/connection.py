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
        """Initialize database schema safely.

        This is non-destructive and creates missing tables, indexes, views,
        triggers, and helper functions without dropping existing data.
        The ``schema_file`` argument is kept for compatibility with the older
        reset-based flow, but the app now uses a production-safe bootstrap.
        """
        try:
            statements = self._safe_schema_statements()
            with self.get_connection() as conn:
                for statement in statements:
                    conn.exec_driver_sql(statement)
            logger.info("Database schema initialized successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    def _safe_schema_statements(self) -> List[str]:
        """Return idempotent schema statements for production-safe bootstrapping."""
        return [
            """
            CREATE TABLE IF NOT EXISTS raw_records (
                id SERIAL PRIMARY KEY,
                upload_batch_id VARCHAR(50) NOT NULL,
                business_name VARCHAR(255) NOT NULL,
                pan VARCHAR(20),
                gstin VARCHAR(20),
                address TEXT,
                pincode VARCHAR(10),
                district VARCHAR(100),
                state VARCHAR(100),
                registration_date DATE,
                last_activity_date DATE,
                department VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cleaned_name VARCHAR(255),
                cleaned_pan VARCHAR(20),
                cleaned_gstin VARCHAR(20),
                cleaned_address TEXT,
                normalized_pincode VARCHAR(10),
                name_phonetic VARCHAR(255)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_raw_records_batch ON raw_records(upload_batch_id)",
            "CREATE INDEX IF NOT EXISTS idx_raw_records_pan ON raw_records(pan)",
            "CREATE INDEX IF NOT EXISTS idx_raw_records_gstin ON raw_records(gstin)",
            "CREATE INDEX IF NOT EXISTS idx_raw_records_pincode ON raw_records(pincode)",
            "CREATE INDEX IF NOT EXISTS idx_raw_records_district ON raw_records(district)",
            "CREATE INDEX IF NOT EXISTS idx_raw_records_state ON raw_records(state)",
            """
            CREATE TABLE IF NOT EXISTS matched_groups (
                id SERIAL PRIMARY KEY,
                ubid VARCHAR(20) NOT NULL UNIQUE,
                master_record_id INTEGER REFERENCES raw_records(id),
                record_ids INTEGER[] NOT NULL,
                match_confidence DECIMAL(5,2) NOT NULL,
                match_tier VARCHAR(20) NOT NULL CHECK (match_tier IN ('Tier1', 'Tier2', 'Tier3')),
                match_reason TEXT,
                matched_fields TEXT[],
                status VARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active', 'Merged', 'Split', 'UnderReview')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_matched_groups_ubid ON matched_groups(ubid)",
            "CREATE INDEX IF NOT EXISTS idx_matched_groups_confidence ON matched_groups(match_confidence)",
            "CREATE INDEX IF NOT EXISTS idx_matched_groups_tier ON matched_groups(match_tier)",
            """
            CREATE TABLE IF NOT EXISTS ubid_registry (
                id SERIAL PRIMARY KEY,
                ubid VARCHAR(20) NOT NULL UNIQUE,
                state_code VARCHAR(2) NOT NULL,
                district_code VARCHAR(3) NOT NULL,
                category VARCHAR(10) NOT NULL,
                sequence_number INTEGER NOT NULL,
                business_name VARCHAR(255),
                primary_pan VARCHAR(20),
                primary_gstin VARCHAR(20),
                business_status VARCHAR(20) NOT NULL CHECK (business_status IN ('Active', 'Dormant', 'Closed')),
                status_reason TEXT,
                total_records INTEGER DEFAULT 1,
                last_activity_date DATE,
                registration_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ubid_registry_ubid ON ubid_registry(ubid)",
            "CREATE INDEX IF NOT EXISTS idx_ubid_registry_status ON ubid_registry(business_status)",
            "CREATE INDEX IF NOT EXISTS idx_ubid_registry_state ON ubid_registry(state_code)",
            """
            CREATE TABLE IF NOT EXISTS match_logs (
                id SERIAL PRIMARY KEY,
                upload_batch_id VARCHAR(50) NOT NULL,
                record1_id INTEGER REFERENCES raw_records(id),
                record2_id INTEGER REFERENCES raw_records(id),
                match_score DECIMAL(5,2) NOT NULL,
                match_tier VARCHAR(20) NOT NULL,
                match_fields JSONB,
                match_decision VARCHAR(20) NOT NULL CHECK (match_decision IN ('AutoMerge', 'NeedsReview', 'KeepSeparate', 'Approved', 'Rejected')),
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_by VARCHAR(100) DEFAULT 'system'
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_match_logs_batch ON match_logs(upload_batch_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_logs_decision ON match_logs(match_decision)",
            """
            CREATE TABLE IF NOT EXISTS review_queue (
                id SERIAL PRIMARY KEY,
                match_group_id INTEGER REFERENCES matched_groups(id),
                record1_id INTEGER REFERENCES raw_records(id),
                record2_id INTEGER REFERENCES raw_records(id),
                match_score DECIMAL(5,2) NOT NULL,
                match_details JSONB,
                status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Escalated')),
                reviewer_notes TEXT,
                assigned_to VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by VARCHAR(100)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status)",
            "CREATE INDEX IF NOT EXISTS idx_review_queue_score ON review_queue(match_score)",
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'update_matched_groups_updated_at'
                ) THEN
                    CREATE TRIGGER update_matched_groups_updated_at
                        BEFORE UPDATE ON matched_groups
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                END IF;
            END
            $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'update_ubid_registry_updated_at'
                ) THEN
                    CREATE TRIGGER update_ubid_registry_updated_at
                        BEFORE UPDATE ON ubid_registry
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                END IF;
            END
            $$;
            """,
            """
            CREATE OR REPLACE VIEW vw_active_businesses AS
            SELECT
                u.ubid,
                u.business_name,
                u.business_status,
                u.state_code,
                u.district_code,
                u.total_records,
                u.last_activity_date,
                mg.match_confidence,
                mg.match_tier
            FROM ubid_registry u
            LEFT JOIN matched_groups mg ON u.ubid = mg.ubid
            WHERE u.business_status = 'Active'
            """,
            """
            CREATE OR REPLACE VIEW vw_pending_reviews AS
            SELECT
                rq.id as review_id,
                rq.match_score,
                rq.match_details,
                rq.status,
                rq.created_at,
                r1.business_name as record1_name,
                r1.pan as record1_pan,
                r1.gstin as record1_gstin,
                r2.business_name as record2_name,
                r2.pan as record2_pan,
                r2.gstin as record2_gstin
            FROM review_queue rq
            JOIN raw_records r1 ON rq.record1_id = r1.id
            JOIN raw_records r2 ON rq.record2_id = r2.id
            WHERE rq.status = 'Pending'
            """,
        ]

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
