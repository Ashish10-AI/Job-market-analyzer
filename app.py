"""
Main application entry point for the Job Market Intelligence Platform.

Streamlit dashboard with five analytical tabs, global sidebar filters,
and comprehensive Plotly visualisations. All data updates dynamically
according to sidebar filters by passing criteria straight to the database layer.

Author: Job Market Intelligence Team
"""

import os
import logging
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import analysis
import database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Job Market Intelligence Platform",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS for premium styling, hover effects, and tag labels
st.markdown(
    """
    <style>
    .skill-tag {
        display: inline-block;
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 4px 10px;
        margin: 2px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .apply-btn {
        display: inline-block;
        background-color: #28a745;
        color: white !important;
        padding: 6px 14px;
        border-radius: 4px;
        text-decoration: none;
        font-weight: bold;
        font-size: 0.9rem;
        transition: background-color 0.2s ease;
    }
    .apply-btn:hover {
        background-color: #218838;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1a73e8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Cached Data Loader (Accepts filters for real-time reactivity)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Filtering database records …")
def load_base_data(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> dict:
    """Fetch filtered analytical datasets from the SQLite database."""
    return {
        "summary": analysis.get_market_summary(role, location, days, min_salary),
        "cities": analysis.get_all_cities(),
        "skills": analysis.get_top_skills(limit=50, role=role, location=location, days=days, min_salary=min_salary),
        "salaries": analysis.get_salary_by_city(role, location, days, min_salary),
        "companies": analysis.get_company_hiring_trends(limit=50, role=role, location=location, days=days, min_salary=min_salary),
        "experience": analysis.get_experience_level_analysis(role, location, days, min_salary),
        "job_types": analysis.get_job_type_distribution(role, location, days, min_salary),
        "recommendations": analysis.get_skills_to_learn_recommendations(limit=15, role=role, location=location, days=days, min_salary=min_salary),
        "salary_trend": analysis.get_salary_trend_over_time(),
        "detailed_offers": analysis.get_detailed_job_offers(role, location, days, min_salary),
    }


@st.cache_data(ttl=600, show_spinner="Preparing CSV export …")
def _build_csv_export(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> bytes:
    """Generate filtered CSV bytes for the download button."""
    df = analysis.get_detailed_job_offers(role, location, days, min_salary)
    if not df.empty:
        return df.to_csv(index=False).encode("utf-8")
    return "No data matches filters".encode("utf-8")


@st.cache_data(ttl=600, show_spinner="Generating PDF report …")
def _build_pdf_bytes(
    role: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = None,
    min_salary: float = 0.0,
) -> bytes:
    """Generate the executive PDF matching current filter settings."""
    try:
        import reporting
        # Pass filtered dataset to the PDF generator
        filtered_data = load_base_data(role, location, days, min_salary)
        path = reporting.generate_pdf_report(filtered_data)
        if path and os.path.exists(path):
            with open(path, "rb") as fh:
                return fh.read()
    except Exception as exc:
        logger.warning("PDF generation failed: %s", exc)
    return b""


# ---------------------------------------------------------------------------
# Reusable Chart Builder Helpers
# ---------------------------------------------------------------------------
def _render_bar(df: pd.DataFrame, x: str, y: str, title: str, color_seq: str = "Blues_r", **kw) -> None:
    """Render a Plotly bar chart with custom styling."""
    if df.empty:
        st.info(f"No data matches criteria for: {title}")
        return
    fig = px.bar(df, x=x, y=y, title=title, color=y, color_continuous_scale=color_seq, **kw)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def _render_pie(df: pd.DataFrame, names: str, values: str, title: str, **kw) -> None:
    """Render a Plotly donut chart."""
    if df.empty:
        st.info(f"No data matches criteria for: {title}")
        return
    fig = px.pie(df, names=names, values=values, title=title, hole=0.4, **kw)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Application Layout
# ---------------------------------------------------------------------------
def main() -> None:
    """Build and present the Streamlit dashboard UI."""

    # 1. Fetch available filters dynamically
    all_cities_list = analysis.get_all_cities()
    
    # Dynamic roles loading
    all_roles_df = database.fetch_dataframe("SELECT DISTINCT title FROM job_postings ORDER BY title ASC")
    all_roles_list = all_roles_df["title"].tolist() if not all_roles_df.empty else []

    # 2. Sidebar Filters Layout
    st.sidebar.title("🔍 Global Filters")
    st.sidebar.markdown("Refine your dashboard insights instantly:")

    selected_role = st.sidebar.selectbox("Job Title / Role", ["All Roles"] + all_roles_list)
    selected_location = st.sidebar.selectbox("Job Location", ["All Locations"] + all_cities_list)
    selected_days = st.sidebar.slider("Jobs Posted Within (Days)", 1, 30, 14, 1)
    min_salary = st.sidebar.number_input("Minimum Salary (₹)", min_value=0, value=0, step=100000)

    st.sidebar.markdown("---")

    if st.sidebar.button("🔄 Clear Cache & Refresh"):
        st.cache_data.clear()
        st.rerun()

    # 3. Load the data using the filter settings
    db_data = load_base_data(selected_role, selected_location, selected_days, float(min_salary))
    summary = db_data["summary"]
    detailed_offers = db_data["detailed_offers"]

    # 4. Sidebar Export Options
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Export Filtered Data")
    st.sidebar.download_button(
        label="📄 Download Data (CSV)",
        data=_build_csv_export(selected_role, selected_location, selected_days, float(min_salary)),
        file_name=f"job_market_export_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    pdf_bytes = _build_pdf_bytes(selected_role, selected_location, selected_days, float(min_salary))
    if pdf_bytes:
        st.sidebar.download_button(
            label="⬇️ Download Executive Report (PDF)",
            data=pdf_bytes,
            file_name="Job_Market_Filtered_Report.pdf",
            mime="application/pdf",
        )
    else:
        st.sidebar.caption("PDF export engine loading...")

    # ===== Dashboard Main Header =====
    st.title("💼 Job Market Intelligence Platform")
    st.markdown(
        f"**Active Filters:** `Role: {selected_role}` · "
        f"`Location: {selected_location}` · "
        f"`Timeframe: Last {selected_days} days` · "
        f"`Min Salary: ₹{min_salary:,}`"
    )

    # ===== Dashboard Tabs =====
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Market Overview",
        "🛠️ Skills Demand",
        "💰 Salary Analysis",
        "🏢 Hiring Companies",
        "🚀 Action Plan & Job Search",
    ])

    # ==================================================================
    # TAB 1 — Market Overview
    # ==================================================================
    with tab1:
        st.subheader("Market Summary KPIs")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"<div class='metric-card'><h4>Active Openings</h4><h2>{summary.get('total_jobs', 0)}</h2></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><h4>Hiring Companies</h4><h2>{summary.get('total_companies', 0)}</h2></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-card'><h4>Skills Tracked</h4><h2>{summary.get('total_skills', 0)}</h2></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='metric-card'><h4>Locations Hiring</h4><h2>{summary.get('total_locations', 0)}</h2></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        
        with col_a:
            df_trend = db_data["salary_trend"]
            if not df_trend.empty:
                fig = px.line(
                    df_trend, x="date", y="avg_salary_offered",
                    title="Average Salary Trend Over Time (Market Baseline)",
                    markers=True,
                )
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Awaiting baseline snapshot records.")

        with col_b:
            _render_bar(
                db_data["experience"], x="experience", y="job_count",
                title="Experience Range Requirements", color_seq="Blues_r",
            )

        col_c, col_d = st.columns([2, 1])
        with col_c:
            _render_pie(
                db_data["job_types"], names="job_type", values="job_count",
                title="Job Type Classification (Remote vs. On-Site)",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
        with col_d:
            st.markdown("### 💡 Quick Insights")
            active_jobs = summary.get("total_jobs", 0)
            if active_jobs > 0:
                st.success(
                    f"Found **{active_jobs}** matching job postings from "
                    f"**{summary.get('total_companies', 0)}** organisations. "
                    f"Use the Action Plan tab to browse details and learn how to apply!"
                )
            else:
                st.warning("No jobs fit the selected criteria. Try easing the minimum salary or location filters.")

    # ==================================================================
    # TAB 2 — Skills Demand
    # ==================================================================
    with tab2:
        st.subheader("In-Demand Technical Skills")
        df_skills = db_data["skills"]

        c1, c2 = st.columns([2, 1])
        with c1:
            _render_bar(
                df_skills.head(15), x="skill_name", y="demand_count",
                title="Top 15 Most Demanded Skills for Selection",
                color_seq="Teal_r",
            )
        with c2:
            st.markdown("#### Skill Count Index")
            st.dataframe(df_skills, use_container_width=True, height=350)

        c3, c4 = st.columns([2, 1])
        with c3:
            if not df_skills.empty:
                fig = px.treemap(
                    df_skills.head(30),
                    path=[px.Constant("Skills Demand Map"), "skill_name"],
                    values="demand_count", color="demand_count",
                    color_continuous_scale="Teal",
                    title="Skill Demand Density Heatmap",
                )
                st.plotly_chart(fig, use_container_width=True)
        with c4:
            st.markdown("### 🛠️ Skills Action Pathway")
            recs = db_data["recommendations"]
            if not recs.empty:
                st.markdown("Acquire these core skills to qualify for current openings:")
                for _, row in recs.head(6).iterrows():
                    st.markdown(f"- 📈 **{row['skill_name'].upper()}** (Highly requested in {summary.get('total_jobs', 0)} postings)")
            else:
                st.info("No skill recommendations match current filters.")

    # ==================================================================
    # TAB 3 — Salary Analysis
    # ==================================================================
    with tab3:
        st.subheader("Compensation Intelligence")
        df_sal = db_data["salaries"]

        c1, c2 = st.columns(2)
        with c1:
            if not df_sal.empty:
                fig = px.bar(
                    df_sal.head(10), y="location", x="jobs_with_salary",
                    orientation="h", title="Salary-Disclosed Postings by City",
                    color="jobs_with_salary", color_continuous_scale="Viridis",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Awaiting salary disclosures.")
        with c2:
            if not df_sal.empty:
                fig = px.scatter(
                    df_sal, x="location", y="jobs_with_salary",
                    size="jobs_with_salary", color="jobs_with_salary",
                    title="Geographic Job Distribution Density",
                )
                st.plotly_chart(fig, use_container_width=True)

    # ==================================================================
    # TAB 4 — Hiring Companies
    # ==================================================================
    with tab4:
        st.subheader("Hiring Organisations Ledger")
        df_comp = db_data["companies"]

        c1, c2 = st.columns([1, 2])
        with c1:
            st.dataframe(df_comp, use_container_width=True, height=400)
        with c2:
            _render_bar(
                df_comp.head(12), x="company_name", y="job_count",
                title="Hiring Volume by Top Companies",
                color_seq="Purples_r",
            )

    # ==================================================================
    # TAB 5 — Action Plan & Job Search
    # ==================================================================
    with tab5:
        st.header("🎯 Job Explorer & Learning Pathways")
        st.markdown(
            "This tab helps you match jobs to hiring companies, identify targeted skill gaps, "
            "and learn how to apply successfully."
        )

        st.markdown("---")

        # Section 1: Job Explorer
        st.subheader("🔍 Active Job Openings Explorer")
        st.markdown("Browse open roles matching your active filters. Click the links to apply on the company portal.")

        if not detailed_offers.empty:
            # We construct a human-readable display of jobs
            for index, row in detailed_offers.iterrows():
                # Format skills as clean HTML tags
                skills_list = [s.strip().upper() for s in str(row["skills"]).split(",") if s.strip()]
                skills_html = "".join([f"<span class='skill-tag'>{s}</span>" for s in skills_list])
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"### {row['job_title']}")
                        st.markdown(
                            f"🏢 **{row['company_name']}** · ⭐ `{row['company_rating']:.1f}/5.0` · "
                            f"📍 `{row['location']}` · 🗓️ `{row['posted_date']}`"
                        )
                    with col2:
                        st.markdown(f"💼 **Exp:** `{row['experience']}` · 💰 **Salary:** `{row['salary']}`")
                        st.markdown(f"**Required Skills:** {skills_html}", unsafe_allow_html=True)
                    with col3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{row['apply_url']}' target='_blank' class='apply-btn'>🔗 Apply Now</a>", unsafe_allow_html=True)
                    
                    st.markdown("<hr style='border:1px solid #eee;'>", unsafe_allow_html=True)
        else:
            st.info("No active openings match the filters in the sidebar. Try selecting 'All Roles' or adjusting the minimum salary.")

        # Section 2: Skill Acquisition Recommendations
        st.markdown("### 🎓 Recommended Learning Pathways")
        
        # Determine the target role for specific advice
        target_advice_role = selected_role if selected_role != "All Roles" else "Data Specialist"
        st.success(f"📘 **Learning Curriculum: How to qualify as a {target_advice_role}**")
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("#### 1. Core Technical Skills")
            st.markdown(
                """
                - **SQL (Structured Query Language):**
                  - *Where to learn:* LeetCode Database Practice, Mode Analytics SQL Tutorial.
                  - *Topics to master:* Joins, Subqueries, CTEs, Window Functions (ROW_NUMBER, LEAD/LAG).
                - **Python (Data Wrangling):**
                  - *Where to learn:* Kaggle Learn Python Course, Real Python.
                  - *Libraries to master:* Pandas, NumPy, Scikit-Learn (for ML roles).
                - **Data Visualization & BI:**
                  - *Where to learn:* Microsoft Power BI Guided Learning, Tableau Public Gallery.
                  - *Topics to master:* Dashboard design principles, Dax formulas, calculated fields.
                """
            )
        
        with c_right:
            st.markdown("#### 2. Specialized Technologies")
            st.markdown(
                """
                - **Modern Data Stack (for Analytics Engineers / Data Engineers):**
                  - *Where to learn:* dbt Learn (free certifications), Snowflake Hands-on Essentials.
                  - *Topics to master:* Data modeling, dimension tables, incremental loads.
                - **Advanced AI / Machine Learning (for Data Scientists & ML Engineers):**
                  - *Where to learn:* Coursera Machine Learning Specialization (DeepLearning.AI), fast.ai.
                  - *Topics to master:* Regression models, neural networks, PyTorch, TensorFlow.
                """
            )

        st.markdown("---")

        # Section 3: Interview Preparation Strategy
        st.subheader("💡 Interview & Application Playbook")
        c_prep1, c_prep2 = st.columns(2)
        with c_prep1:
            st.warning("⚠️ **Technical Round Strategy**")
            st.markdown(
                "1. **SQL Live Coding:** Practice writing syntax on a virtual whiteboard. Be ready to explain joins vs. unions.\n"
                "2. **Portfolio Walkthrough:** Prepare a 5-minute explanation of a data project, emphasizing business impact over code.\n"
                "3. **Data Quality Case:** Be ready for the question: *'What would you do if a key dashboard metric dropped by 20% overnight?'*"
            )
        with c_prep2:
            st.error("🚀 **Star Method Behavioural Prep**")
            st.markdown(
                "- **Situation:** Describe a complex market data project or database project you completed.\n"
                "- **Task:** Detail the challenge (e.g. data isolation, missing salaries, zero card responses).\n"
                "- **Action:** Explain how you refactored the scraper to include dynamic fallback seeds, registered sqlite functions, etc.\n"
                "- **Result:** Share the outcome (e.g., 100+ fully-populated interactive jobs across 10 profiles rendering on Streamlit)."
            )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
