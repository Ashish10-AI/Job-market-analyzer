"""
Database operations for the Job Market Intelligence Platform.

This module manages all data persistence and retrieval using SQLite.
It provides a context-managed connection pool, schema initialization,
and CRUD operations with full UPSERT support.

Author: Job Market Intelligence Team
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — DB is located directly in the project root directory
# ---------------------------------------------------------------------------
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(BASE_DIR, "jobs.db")


# ---------------------------------------------------------------------------
# Connection Management
# ---------------------------------------------------------------------------
def _extract_min_salary(salary_str: str) -> float:
    """Helper to extract the minimum salary value from a range string for SQLite queries."""
    if not salary_str or salary_str == "Not Disclosed":
        return 0.0
    try:
        clean = salary_str.replace("₹", "").replace(",", "").replace("PA", "").strip()
        if "-" in clean:
            parts = clean.split("-")
            return float(parts[0].strip())
        return float(clean)
    except Exception:
        return 0.0


@contextmanager
def get_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield a managed SQLite connection with WAL mode and foreign-key support."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path, timeout=15)
        # Register custom functions for advanced SQL filtering
        conn.create_function("EXTRACT_MIN_SALARY", 1, _extract_min_salary)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------
_TABLE_SCHEMAS: Dict[str, str] = {
    "company_hiring": """
        CREATE TABLE IF NOT EXISTS company_hiring (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            company_name  TEXT      UNIQUE NOT NULL,
            industry      TEXT,
            rating        REAL      CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
            last_updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "job_postings": """
        CREATE TABLE IF NOT EXISTS job_postings (
            id           INTEGER   PRIMARY KEY AUTOINCREMENT,
            job_id       TEXT      UNIQUE NOT NULL,
            title        TEXT      NOT NULL,
            company_id   INTEGER,
            location     TEXT,
            experience   TEXT,
            salary       TEXT,
            posted_date  DATE,
            scraped_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company_hiring(id) ON DELETE SET NULL
        );
    """,
    "skills_demand": """
        CREATE TABLE IF NOT EXISTS skills_demand (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            skill_name    TEXT      UNIQUE NOT NULL,
            demand_count  INTEGER   DEFAULT 1 CHECK (demand_count >= 0),
            last_seen     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "job_skills": """
        CREATE TABLE IF NOT EXISTS job_skills (
            job_id       TEXT,
            skill_name   TEXT,
            PRIMARY KEY (job_id, skill_name),
            FOREIGN KEY (job_id) REFERENCES job_postings(job_id) ON DELETE CASCADE
        );
    """,
    "daily_market_snapshot": """
        CREATE TABLE IF NOT EXISTS daily_market_snapshot (
            id                 INTEGER   PRIMARY KEY AUTOINCREMENT,
            snapshot_date      DATE      UNIQUE NOT NULL,
            total_active_jobs  INTEGER   DEFAULT 0,
            new_jobs_added     INTEGER   DEFAULT 0,
            top_hiring_sectors TEXT,
            avg_salary_offered REAL,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
}

_INDEX_STATEMENTS: List[str] = [
    "CREATE INDEX IF NOT EXISTS idx_job_postings_job_id     ON job_postings(job_id);",
    "CREATE INDEX IF NOT EXISTS idx_job_postings_company_id ON job_postings(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_job_postings_location   ON job_postings(location);",
    "CREATE INDEX IF NOT EXISTS idx_job_postings_posted     ON job_postings(posted_date);",
    "CREATE INDEX IF NOT EXISTS idx_company_name            ON company_hiring(company_name);",
    "CREATE INDEX IF NOT EXISTS idx_skills_name             ON skills_demand(skill_name);",
    "CREATE INDEX IF NOT EXISTS idx_job_skills_map          ON job_skills(job_id, skill_name);",
    "CREATE INDEX IF NOT EXISTS idx_snapshot_date           ON daily_market_snapshot(snapshot_date);",
]


# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------
def create_database() -> None:
    """Create all tables and indexes if they do not already exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for table_name, ddl in _TABLE_SCHEMAS.items():
                cursor.execute(ddl)
                logger.info("Table '%s' verified/created.", table_name)
            for idx_stmt in _INDEX_STATEMENTS:
                cursor.execute(idx_stmt)
            conn.commit()
            logger.info("Database schema and indexes creation successful.")
    except sqlite3.Error as exc:
        logger.error("Failed to create database: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Generic Query Helpers
# ---------------------------------------------------------------------------
def execute_query(
    query: str,
    params: tuple = (),
    commit: bool = False,
) -> Optional[List[sqlite3.Row]]:
    """Execute an arbitrary SQL statement with parameterised inputs."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
                return None
            return cursor.fetchall()
    except sqlite3.Error as exc:
        logger.error("Query execution error: %s | Query: %s", exc, query[:120])
        raise


def fetch_dataframe(query: str, params: tuple = ()) -> pd.DataFrame:
    """Run a SELECT and return results as a Pandas DataFrame."""
    try:
        with get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as exc:
        logger.error("Error fetching dataframe: %s", exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# CRUD — Companies
# ---------------------------------------------------------------------------
def insert_company(company_data: Dict[str, Any]) -> Optional[int]:
    """Insert or update a company record using UPSERT logic."""
    query = """
        INSERT INTO company_hiring (company_name, industry, rating, last_updated)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(company_name) DO UPDATE SET
            industry     = excluded.industry,
            rating       = excluded.rating,
            last_updated = CURRENT_TIMESTAMP
        RETURNING id;
    """
    params = (
        company_data.get("company_name"),
        company_data.get("industry"),
        company_data.get("rating"),
    )
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.commit()
            return result["id"] if result else None
    except sqlite3.Error as exc:
        logger.error("Error inserting company '%s': %s", company_data.get("company_name"), exc)
        return None


# ---------------------------------------------------------------------------
# CRUD — Job Postings
# ---------------------------------------------------------------------------
def insert_job(job_data: Dict[str, Any]) -> bool:
    """Insert or update a job posting, and populate the job_skills map."""
    company_id: Optional[int] = None
    company_name = job_data.get("company_name")
    if company_name:
        company_id = insert_company({
            "company_name": company_name,
            "industry": job_data.get("industry"),
            "rating": job_data.get("company_rating"),
        })

    query = """
        INSERT INTO job_postings
            (job_id, title, company_id, location, experience, salary, posted_date, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(job_id) DO UPDATE SET
            title       = excluded.title,
            company_id  = excluded.company_id,
            location    = excluded.location,
            experience  = excluded.experience,
            salary      = excluded.salary,
            posted_date = excluded.posted_date,
            scraped_at  = CURRENT_TIMESTAMP;
    """
    params = (
        job_data.get("job_id"),
        job_data.get("title"),
        company_id,
        job_data.get("location"),
        job_data.get("experience"),
        job_data.get("salary"),
        job_data.get("posted_date"),
    )
    try:
        with get_connection() as conn:
            conn.execute(query, params)
            
            # Populate skills linking table for this job
            skills = job_data.get("skills", [])
            for skill in skills:
                if skill and skill.strip():
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO job_skills (job_id, skill_name)
                        VALUES (?, ?);
                        """,
                        (job_data.get("job_id"), skill.strip().lower())
                    )
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Error inserting job '%s': %s", job_data.get("job_id"), exc)
        return False


# ---------------------------------------------------------------------------
# CRUD — Skills
# ---------------------------------------------------------------------------
def insert_skill(skill_name: str) -> bool:
    """Insert a skill or increment its demand counter via UPSERT."""
    if not skill_name or not skill_name.strip():
        return False

    query = """
        INSERT INTO skills_demand (skill_name, demand_count, last_seen)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(skill_name) DO UPDATE SET
            demand_count = demand_count + 1,
            last_seen    = CURRENT_TIMESTAMP;
    """
    try:
        with get_connection() as conn:
            conn.execute(query, (skill_name.strip().lower(),))
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Error inserting skill '%s': %s", skill_name, exc)
        return False


# ---------------------------------------------------------------------------
# CRUD — Daily Snapshots
# ---------------------------------------------------------------------------
def update_daily_snapshot(snapshot_data: Dict[str, Any]) -> bool:
    """Insert or update the daily market snapshot."""
    query = """
        INSERT INTO daily_market_snapshot
            (snapshot_date, total_active_jobs, new_jobs_added,
             top_hiring_sectors, avg_salary_offered, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(snapshot_date) DO UPDATE SET
            total_active_jobs  = excluded.total_active_jobs,
            new_jobs_added     = excluded.new_jobs_added,
            top_hiring_sectors = excluded.top_hiring_sectors,
            avg_salary_offered = excluded.avg_salary_offered,
            created_at         = CURRENT_TIMESTAMP;
    """
    params = (
        snapshot_data.get("snapshot_date"),
        snapshot_data.get("total_active_jobs", 0),
        snapshot_data.get("new_jobs_added", 0),
        snapshot_data.get("top_hiring_sectors"),
        snapshot_data.get("avg_salary_offered"),
    )
    try:
        with get_connection() as conn:
            conn.execute(query, params)
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Error updating snapshot for '%s': %s", snapshot_data.get("snapshot_date"), exc)
        return False


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
def close_connection() -> None:
    """No-op provided for interface completeness."""
    pass


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger.info("Initializing Database Setup...")
    create_database()
    logger.info("Database setup complete. File: %s", DB_PATH)
