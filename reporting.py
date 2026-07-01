"""
Reporting module for the Job Market Intelligence Platform.

Generates professional PDF executive reports with embedded Plotly charts
and provides CSV export functionality.  The ``reports/`` directory is
auto-created at import time.

Author: Job Market Intelligence Team
"""

import os
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.express as px
from fpdf import FPDF

logger = logging.getLogger(__name__)

# Auto-create reports directory
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR: str = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# PDF Subclass — Header / Footer
# ---------------------------------------------------------------------------
class MarketReportPDF(FPDF):
    """Custom FPDF subclass with branded header and page numbering."""

    def header(self) -> None:
        """Render centred report title at the top of every page."""
        self.set_font("helvetica", "B", 16)
        self.cell(0, 10, "Job Market Intelligence - Executive Report", align="C")
        self.ln(6)
        self.set_font("helvetica", "I", 9)
        self.cell(
            0, 6,
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            align="C",
        )
        self.ln(12)

    def footer(self) -> None:
        """Render page number at the bottom of every page."""
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_text(text: str) -> str:
    """Encode *text* to latin-1 to avoid fpdf UnicodeEncodeError.

    Args:
        text: Arbitrary string that may contain non-latin characters.

    Returns:
        A latin-1 safe string with unsupported chars replaced by ``?``.
    """
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _generate_chart_image(fig, filename: str) -> Optional[str]:
    """Save a Plotly figure as a PNG for PDF embedding.

    Args:
        fig:      Plotly figure object.
        filename: Target filename within ``REPORTS_DIR``.

    Returns:
        Absolute path to the saved image, or ``None`` on failure.
    """
    filepath = os.path.join(REPORTS_DIR, filename)
    try:
        fig.write_image(filepath, width=800, height=400)
        return filepath
    except Exception as exc:
        logger.warning("Chart export failed (%s): %s", filename, exc)
        return None


def _add_section(pdf: FPDF, number: int, title: str) -> None:
    """Write a numbered section heading into the PDF.

    Args:
        pdf:    Active FPDF instance.
        number: Section number.
        title:  Section heading text.
    """
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, f"{number}. {title}", ln=True)
    pdf.set_font("helvetica", "", 11)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_pdf_report(db_data: dict) -> str:
    """Compile a multi-page PDF executive report from cached dashboard data.

    Sections: Market Summary, Salary Insights, Skill Trends, Top Companies.
    Each section gracefully handles missing / empty data.

    Args:
        db_data: The same dictionary returned by ``load_base_data()`` in app.py.

    Returns:
        Absolute filesystem path to the generated PDF.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(REPORTS_DIR, f"market_report_{timestamp}.pdf")

    pdf = MarketReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- 1. Market Summary ---
    _add_section(pdf, 1, "Market Summary")
    summary = db_data.get("summary", {})
    if summary and summary.get("total_jobs", 0) > 0:
        for label, key in [
            ("Total Active Jobs Tracked", "total_jobs"),
            ("Total Companies Hiring", "total_companies"),
            ("Unique Skills Extracted", "total_skills"),
            ("Active Locations", "total_locations"),
        ]:
            pdf.cell(0, 8, f"  {label}: {summary.get(key, 0)}", ln=True)
    else:
        pdf.cell(0, 8, "  No market data available (database is empty).", ln=True)
    pdf.ln(5)

    # --- 2. Salary Insights ---
    _add_section(pdf, 2, "Salary Insights")
    salaries = db_data.get("salaries", pd.DataFrame())
    if not salaries.empty:
        for _, row in salaries.head(5).iterrows():
            pdf.cell(
                0, 8,
                _safe_text(f"  - {row['location']}: {row['jobs_with_salary']} jobs disclosing salary"),
                ln=True,
            )
    else:
        pdf.cell(0, 8, "  No salary disclosure data available.", ln=True)
    pdf.ln(5)

    # --- 3. Skill Trends ---
    _add_section(pdf, 3, "Top Skill Trends")
    skills = db_data.get("skills", pd.DataFrame())
    if not skills.empty:
        for _, row in skills.head(5).iterrows():
            pdf.cell(
                0, 8,
                _safe_text(f"  - {str(row['skill_name']).title()}: {row['demand_count']} mentions"),
                ln=True,
            )
        fig = px.bar(
            skills.head(10), x="skill_name", y="demand_count",
            title="Top 10 Market Skills",
        )
        img = _generate_chart_image(fig, "skills_chart.png")
        if img:
            pdf.image(img, w=170)
            pdf.ln(5)
    else:
        pdf.cell(0, 8, "  No skill data available.", ln=True)
    pdf.ln(5)

    # --- 4. Top Companies ---
    pdf.add_page()
    _add_section(pdf, 4, "Top Hiring Companies")
    companies = db_data.get("companies", pd.DataFrame())
    if not companies.empty:
        for _, row in companies.head(5).iterrows():
            pdf.cell(
                0, 8,
                _safe_text(f"  - {row['company_name']}: {row['job_count']} open roles"),
                ln=True,
            )
        fig = px.bar(
            companies.head(10), x="company_name", y="job_count",
            title="Hiring Volume — Top Organisations",
        )
        img = _generate_chart_image(fig, "companies_chart.png")
        if img:
            pdf.image(img, w=170)
    else:
        pdf.cell(0, 8, "  No company data available.", ln=True)

    pdf.output(filepath)
    logger.info("PDF report saved to %s", filepath)
    return filepath
