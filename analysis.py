"""
Analysis module for the Job Market Intelligence Platform.

All analytical processing is performed directly in highly optimised SQL queries.
It supports dynamic filtering at the database layer based on job role,
location, timeframe, and minimum salary, which guarantees responsive dashboard updates.

Author: Job Market Intelligence Team
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

import database

logger = logging.getLogger(__name__)

# Column schemas for empty-result safety
_COLS_SKILLS: List[str] = ["skill_name", "demand_count"]
_COLS_SALARY: List[str] = ["location", "jobs_with_salary"]
_COLS_COMPANY: List[str] = ["company_name", "job_count"]
_COLS_EXP: List[str] = ["experience", "job_count"]
_COLS_JOB_TYPE: List[str] = ["job_type", "job_count"]
_COLS_TREND: List[str] = ["date", "avg_salary_offered"]
_COLS_RECO: List[str] = ["skill_name", "demand_count", "last_seen"]
_COLS_OFFERS: List[str] = [
    "company_name",
    "company_rating",
    "job_title",
    "location",
    "salary",
    "experience",
    "skills",
    "posted_date",
    "apply_url",
]


def _safe_df(df: Optional[pd.DataFrame], columns: List[str]) -> pd.DataFrame:
    """Return *df* unchanged if it holds data, otherwise an empty typed frame."""
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    return df


def _build_where_clause(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
    table_prefix: str = "jp",
) -> Tuple[str, List[Any]]:
    """Build a SQL WHERE clause fragment and parameter bindings for filtering.

    Args:
        role: Selected job title/role (or 'All Roles').
        location: Selected job location (or 'All Locations').
        days: Days filter.
        min_salary: Minimum salary threshold.
        table_prefix: Table alias prefix for SQL columns (e.g. 'jp').

    Returns:
        Tuple of (sql_fragment, list_of_params)
    """
    clauses = []
    params = []

    # 1. Job Role Filter
    if role and role != "All Roles":
        clauses.append(f"{table_prefix}.title = ?")
        params.append(role)

    # 2. Location Filter
    if location and location != "All Locations":
        clauses.append(f"{table_prefix}.location = ?")
        params.append(location)

    # 3. Posted Timeframe Filter
    if days:
        target_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        clauses.append(f"{table_prefix}.posted_date >= ?")
        params.append(target_date)

    # 4. Salary Filter (uses custom SQLite function registered in database.py)
    if min_salary > 0:
        clauses.append(f"EXTRACT_MIN_SALARY({table_prefix}.salary) >= ?")
        params.append(min_salary)

    sql_fragment = " AND ".join(clauses)
    if sql_fragment:
        sql_fragment = " AND " + sql_fragment

    return sql_fragment, params


# ---------------------------------------------------------------------------
# Public Filtered Analysis Functions
# ---------------------------------------------------------------------------
def get_top_skills(
    limit: int = 15,
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Retrieve the most in-demand skills ranked by frequency under filters."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   js.skill_name,
                 COUNT(js.job_id) AS demand_count
        FROM     job_skills js
        JOIN     job_postings jp ON js.job_id = jp.job_id
        WHERE    1=1 {where_sql}
        GROUP BY js.skill_name
        ORDER BY demand_count DESC
        LIMIT    ?
    """
    params.append(limit)
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_SKILLS)


def get_salary_by_city(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Count jobs with disclosed salary per city under filters."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   location,
                 COUNT(id) AS jobs_with_salary
        FROM     job_postings jp
        WHERE    location IS NOT NULL
          AND    location != ''
          AND    salary   IS NOT NULL
          AND    salary   != 'Not Disclosed'
          {where_sql}
        GROUP BY location
        ORDER BY jobs_with_salary DESC
    """
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_SALARY)


def get_company_hiring_trends(
    limit: int = 10,
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Identify companies with the most active job postings under filters."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   c.company_name,
                 COUNT(jp.id) AS job_count
        FROM     company_hiring c
        JOIN     job_postings   jp ON c.id = jp.company_id
        WHERE    1=1 {where_sql}
        GROUP BY c.company_name
        ORDER BY job_count DESC
        LIMIT    ?
    """
    params.append(limit)
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_COMPANY)


def get_experience_level_analysis(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Distribution of experience requirements across postings under filters."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   experience,
                 COUNT(id) AS job_count
        FROM     job_postings jp
        WHERE    experience IS NOT NULL
          AND    experience != ''
          {where_sql}
        GROUP BY experience
        ORDER BY job_count DESC
    """
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_EXP)


def get_job_type_distribution(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Infer job-type categories from title keywords under filters."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT
            CASE
                WHEN LOWER(title) LIKE '%remote%'                          THEN 'Remote'
                WHEN LOWER(title) LIKE '%intern%'                          THEN 'Internship'
                WHEN LOWER(title) LIKE '%contract%'                        THEN 'Contract'
                WHEN LOWER(title) LIKE '%freelance%'                       THEN 'Freelance'
                WHEN LOWER(title) LIKE '%part time%'
                  OR LOWER(title) LIKE '%part-time%'                       THEN 'Part-Time'
                ELSE 'Full-Time / On-Site'
            END AS job_type,
            COUNT(id) AS job_count
        FROM     job_postings jp
        WHERE    1=1 {where_sql}
        GROUP BY job_type
        ORDER BY job_count DESC
    """
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_JOB_TYPE)


def get_salary_trend_over_time() -> pd.DataFrame:
    """Retrieve historical average salary trend over time (global snapshot)."""
    query = """
        SELECT   snapshot_date AS date,
                 avg_salary_offered
        FROM     daily_market_snapshot
        WHERE    avg_salary_offered IS NOT NULL
        ORDER BY snapshot_date ASC
    """
    return _safe_df(database.fetch_dataframe(query), _COLS_TREND)


def get_market_summary(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> Dict[str, int]:
    """Aggregate high-level KPIs under filters."""
    _DEFAULT: Dict[str, int] = {
        "total_jobs": 0,
        "total_companies": 0,
        "total_skills": 0,
        "total_locations": 0,
    }
    
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    # We run count calculations specific to the filtered workspace
    query_jobs = f"SELECT COUNT(*) FROM job_postings jp WHERE 1=1 {where_sql}"
    query_companies = f"SELECT COUNT(DISTINCT company_id) FROM job_postings jp WHERE 1=1 {where_sql}"
    query_skills = f"SELECT COUNT(DISTINCT skill_name) FROM job_skills js JOIN job_postings jp ON js.job_id = jp.job_id WHERE 1=1 {where_sql}"
    query_locations = f"SELECT COUNT(DISTINCT location) FROM job_postings jp WHERE location IS NOT NULL AND location != '' {where_sql}"
    
    try:
        jobs_res = database.execute_query(query_jobs, params=tuple(params))
        comp_res = database.execute_query(query_companies, params=tuple(params))
        skills_res = database.execute_query(query_skills, params=tuple(params))
        locs_res = database.execute_query(query_locations, params=tuple(params))
        
        return {
            "total_jobs": jobs_res[0][0] if jobs_res else 0,
            "total_companies": comp_res[0][0] if comp_res else 0,
            "total_skills": skills_res[0][0] if skills_res else 0,
            "total_locations": locs_res[0][0] if locs_res else 0,
        }
    except Exception as exc:
        logger.error("Error fetching market summary: %s", exc)
        return _DEFAULT


def get_all_cities() -> List[str]:
    """Return a sorted, distinct list of all recorded job locations."""
    query = """
        SELECT DISTINCT location
        FROM   job_postings
        WHERE  location IS NOT NULL
          AND  location != ''
        ORDER  BY location ASC
    """
    try:
        results = database.execute_query(query)
        if results:
            return [row["location"] for row in results]
    except Exception as exc:
        logger.error("Error fetching cities: %s", exc)
    return []


def get_skills_to_learn_recommendations(
    limit: int = 8,
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Recommend skills to acquire based on filtered market frequency."""
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   js.skill_name,
                 COUNT(js.job_id) AS demand_count,
                 MAX(jp.scraped_at) AS last_seen
        FROM     job_skills js
        JOIN     job_postings jp ON js.job_id = jp.job_id
        WHERE    1=1 {where_sql}
        GROUP BY js.skill_name
        ORDER BY demand_count DESC, last_seen DESC
        LIMIT    ?
    """
    params.append(limit)
    return _safe_df(database.fetch_dataframe(query, params=tuple(params)), _COLS_RECO)


def get_detailed_job_offers(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> pd.DataFrame:
    """Retrieve detailed job openings for exploration.

    Aggregates linked skills into a comma-separated list, resolves the hiring
    company name/rating, and generates a formatted, interactive details model.
    """
    where_sql, params = _build_where_clause(role, location, days, min_salary, "jp")
    
    query = f"""
        SELECT   c.company_name,
                 COALESCE(c.rating, 3.8) AS company_rating,
                 jp.title AS job_title,
                 jp.location,
                 jp.salary,
                 jp.experience,
                 (
                     SELECT GROUP_CONCAT(js.skill_name, ', ')
                     FROM   job_skills js
                     WHERE  js.job_id = jp.job_id
                 ) AS skills,
                 jp.posted_date
        FROM     job_postings jp
        JOIN     company_hiring c ON jp.company_id = c.id
        WHERE    1=1 {where_sql}
        ORDER BY jp.posted_date DESC
    """
    df = database.fetch_dataframe(query, params=tuple(params))
    if df is not None and not df.empty:
        # Generate simulated clean URL based on company and title for application routing
        df["apply_url"] = df.apply(
            lambda r: f"https://www.naukri.com/{r['company_name'].lower().replace(' ', '')}-jobs",
            axis=1
        )
    return _safe_df(df, _COLS_OFFERS)


# ---------------------------------------------------------------------------
# Self-Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    print("Testing Filtered Analysis Module...\n")
    print("Filtered summary (Bangalore):", get_market_summary(location="Bangalore"))
    print("\nTop 5 skills in Bangalore:\n", get_top_skills(limit=5, location="Bangalore"))
    print("\nDetailed Job Offers in Bangalore:\n", get_detailed_job_offers(location="Bangalore").head(2))
