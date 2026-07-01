"""
Scraper module for the Job Market Intelligence Platform.

This module houses the dynamic simulated data seed engine, providing at least
100 high-quality job postings distributed across 10 distinct job profiles
(10 jobs per profile) to satisfy advanced portfolio demo needs.

Author: Job Market Intelligence Team
"""

import hashlib
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

import database

logger = logging.getLogger(__name__)

# Target roles to cover the complete modern data ecosystem
TARGET_ROLES: List[str] = [
    "Data Analyst",
    "Junior Data Analyst",
    "Business Analyst",
    "Analytics Engineer",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "BI Developer",
    "Product Analyst",
    "Quantitative Analyst",
]

# CSS selectors for static scraping attempts
_CARD_SELECTORS: str = "div.srp-jobtuple-wrapper, article.jobTuple, div.jobTuple"
MAX_PAGES_PER_ROLE: int = 2

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ---------------------------------------------------------------------------
# Simulated Data Engine (10 Profiles x 10 Jobs = 100 Jobs minimum)
# ---------------------------------------------------------------------------
SIMULATED_JOBS: Dict[str, List[Dict[str, Any]]] = {
    "Data Analyst": [
        {"title": "Data Analyst", "company_name": "Tata Consultancy Services (TCS)", "location": "Bangalore", "experience": "2-4 years", "salary": "₹6,00,000 - ₹9,50,000 PA", "skills": ["SQL", "Power BI", "Python", "Excel"], "company_rating": 3.9, "industry": "IT Services"},
        {"title": "Business Intelligence Analyst", "company_name": "Accenture", "location": "Hyderabad", "experience": "1-3 years", "salary": "₹5,50,000 - ₹8,00,000 PA", "skills": ["SQL", "Tableau", "Excel", "Alteryx"], "company_rating": 4.1, "industry": "Consulting"},
        {"title": "Senior Data Analyst", "company_name": "Google", "location": "Bangalore", "experience": "4-7 years", "salary": "₹18,00,000 - ₹28,00,000 PA", "skills": ["SQL", "Python", "R", "BigQuery", "Looker"], "company_rating": 4.6, "industry": "Internet"},
        {"title": "Data Operations Analyst", "company_name": "Amazon", "location": "Chennai", "experience": "2-5 years", "salary": "₹8,00,000 - ₹12,00,000 PA", "skills": ["SQL", "Redshift", "Excel", "Tableau"], "company_rating": 4.3, "industry": "E-Commerce"},
        {"title": "Data Analyst II", "company_name": "Microsoft", "location": "Hyderabad", "experience": "3-6 years", "salary": "₹15,00,000 - ₹22,00,000 PA", "skills": ["SQL", "Azure", "Power BI", "Python"], "company_rating": 4.5, "industry": "Software"},
        {"title": "Marketing Data Analyst", "company_name": "Flipkart", "location": "Bangalore", "experience": "1-3 years", "salary": "₹7,00,000 - ₹10,00,000 PA", "skills": ["Google Analytics", "SQL", "Excel", "Tableau"], "company_rating": 4.0, "industry": "E-Commerce"},
        {"title": "Supply Chain Data Analyst", "company_name": "Wipro", "location": "Pune", "experience": "2-4 years", "salary": "₹5,00,000 - ₹7,50,000 PA", "skills": ["SQL", "Excel", "Power BI", "ERP"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "Financial Data Analyst", "company_name": "JPMorgan Chase & Co.", "location": "Mumbai", "experience": "3-5 years", "salary": "₹12,00,000 - ₹16,50,000 PA", "skills": ["SQL", "Python", "Excel", "Financial Modeling"], "company_rating": 4.2, "industry": "Financial Services"},
        {"title": "Clinical Data Analyst", "company_name": "Optum", "location": "Gurgaon", "experience": "2-5 years", "salary": "₹8,50,000 - ₹13,00,000 PA", "skills": ["SQL", "SAS", "Python", "Tableau"], "company_rating": 4.0, "industry": "Healthcare"},
        {"title": "Product Data Analyst", "company_name": "Adobe", "location": "Noida", "experience": "3-6 years", "salary": "₹16,00,000 - ₹24,00,000 PA", "skills": ["SQL", "Python", "Tableau", "A/B Testing"], "company_rating": 4.4, "industry": "Software"}
    ],
    "Junior Data Analyst": [
        {"title": "Junior Data Analyst (Fresher)", "company_name": "Cognizant", "location": "Chennai", "experience": "0-1 years", "salary": "₹3,50,000 - ₹4,80,000 PA", "skills": ["SQL", "Excel", "Power BI"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Associate Data Analyst", "company_name": "Infosys", "location": "Mysore", "experience": "0-2 years", "salary": "₹3,60,000 - ₹5,00,000 PA", "skills": ["SQL", "Excel", "Python"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Junior Business Analyst", "company_name": "Capgemini", "location": "Mumbai", "experience": "0-1 years", "salary": "₹4,00,000 - ₹5,50,000 PA", "skills": ["SQL", "Excel", "PowerPoint"], "company_rating": 3.9, "industry": "IT Services"},
        {"title": "Graduate Analyst Trainee", "company_name": "HCLTech", "location": "Noida", "experience": "0-1 years", "salary": "₹3,25,000 - ₹4,50,000 PA", "skills": ["SQL", "Excel", "Documentation"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "Junior Data Analyst - Remote", "company_name": "Tech Mahindra", "location": "Remote", "experience": "0-2 years", "salary": "₹4,20,000 - ₹6,00,000 PA", "skills": ["SQL", "Power BI", "Excel"], "company_rating": 3.6, "industry": "IT Services"},
        {"title": "Data Analyst Trainee", "company_name": "Genpact", "location": "Gurgaon", "experience": "0-1 years", "salary": "₹3,00,000 - ₹4,20,000 PA", "skills": ["Excel", "Data Cleansing", "Basic SQL"], "company_rating": 3.7, "industry": "BPO"},
        {"title": "Junior Analyst - Insights", "company_name": "Paytm", "location": "Noida", "experience": "0-2 years", "salary": "₹5,00,000 - ₹7,00,000 PA", "skills": ["SQL", "Tableau", "Excel"], "company_rating": 3.5, "industry": "FinTech"},
        {"title": "Junior Operations Analyst", "company_name": "Zomato", "location": "Gurgaon", "experience": "0-2 years", "salary": "₹6,00,000 - ₹8,50,000 PA", "skills": ["Google Sheets", "SQL", "Python"], "company_rating": 4.1, "industry": "Internet"},
        {"title": "Associate Analyst", "company_name": "Dell Technologies", "location": "Bangalore", "experience": "0-2 years", "salary": "₹4,80,000 - ₹6,80,000 PA", "skills": ["SQL", "Excel", "Power BI"], "company_rating": 4.2, "industry": "Hardware"},
        {"title": "Junior Risk Data Analyst", "company_name": "HSBC", "location": "Hyderabad", "experience": "0-2 years", "salary": "₹5,50,000 - ₹7,80,000 PA", "skills": ["SQL", "SAS", "Excel"], "company_rating": 3.9, "industry": "Banking"}
    ],
    "Business Analyst": [
        {"title": "Business Analyst", "company_name": "Accenture", "location": "Bangalore", "experience": "2-5 years", "salary": "₹7,50,000 - ₹11,00,000 PA", "skills": ["Agile", "Jira", "SQL", "Requirements Gathering"], "company_rating": 4.1, "industry": "Consulting"},
        {"title": "IT Business Analyst", "company_name": "Cognizant", "location": "Pune", "experience": "3-6 years", "salary": "₹6,50,000 - ₹10,00,000 PA", "skills": ["SQL", "SDLC", "Jira", "BRD"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Associate Business Analyst", "company_name": "Infosys", "location": "Bangalore", "experience": "0-1 years", "salary": "₹4,00,000 - ₹5,50,000 PA", "skills": ["Excel", "Communication", "Basic SQL"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Product Business Analyst", "company_name": "Ola Cabs", "location": "Bangalore", "experience": "1-3 years", "salary": "₹8,00,000 - ₹13,00,000 PA", "skills": ["SQL", "Tableau", "Product Specs"], "company_rating": 3.4, "industry": "Internet"},
        {"title": "Consultant - Business Analysis", "company_name": "Deloitte", "location": "Hyderabad", "experience": "3-5 years", "salary": "₹11,00,000 - ₹16,00,000 PA", "skills": ["Business Strategy", "SQL", "Tableau"], "company_rating": 4.0, "industry": "Consulting"},
        {"title": "Business Analyst - Finance", "company_name": "EY (Ernst & Young)", "location": "Mumbai", "experience": "2-4 years", "salary": "₹8,50,000 - ₹12,50,000 PA", "skills": ["Financial Analysis", "SQL", "Excel"], "company_rating": 3.9, "industry": "Accounting"},
        {"title": "Junior Business Systems Analyst", "company_name": "Wipro", "location": "Chennai", "experience": "1-2 years", "salary": "₹4,50,000 - ₹6,50,000 PA", "skills": ["Excel", "SQL", "Requirements Analysis"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "Retail Business Analyst", "company_name": "Target", "location": "Bangalore", "experience": "2-5 years", "salary": "₹9,00,000 - ₹14,00,000 PA", "skills": ["SQL", "Excel", "Data Visualization"], "company_rating": 4.1, "industry": "Retail"},
        {"title": "Senior Consultant Analyst", "company_name": "McKinsey & Company", "location": "Gurgaon", "experience": "4-8 years", "salary": "₹20,00,000 - ₹32,00,000 PA", "skills": ["Problem Solving", "Management Consulting", "SQL"], "company_rating": 4.4, "industry": "Consulting"},
        {"title": "Business Systems Analyst II", "company_name": "Cisco", "location": "Bangalore", "experience": "3-6 years", "salary": "₹14,00,000 - ₹20,00,000 PA", "skills": ["Systems Design", "SQL", "Agile"], "company_rating": 4.3, "industry": "Hardware"}
    ],
    "Analytics Engineer": [
        {"title": "Analytics Engineer", "company_name": "Swiggy", "location": "Bangalore", "experience": "2-4 years", "salary": "₹12,00,000 - ₹18,00,000 PA", "skills": ["dbt", "SQL", "Snowflake", "Git"], "company_rating": 4.0, "industry": "Internet"},
        {"title": "Analytics Engineer - Remote", "company_name": "Razorpay", "location": "Remote", "experience": "1-3 years", "salary": "₹10,00,000 - ₹15,00,000 PA", "skills": ["SQL", "dbt", "Python", "Airflow"], "company_rating": 4.2, "industry": "FinTech"},
        {"title": "Senior Analytics Engineer", "company_name": "Stripe", "location": "Bangalore", "experience": "4-7 years", "salary": "₹25,00,000 - ₹38,00,000 PA", "skills": ["SQL", "dbt", "Python", "Redshift"], "company_rating": 4.3, "industry": "FinTech"},
        {"title": "Junior Analytics Engineer", "company_name": "Cred", "location": "Bangalore", "experience": "0-2 years", "salary": "₹8,00,000 - ₹12,00,000 PA", "skills": ["SQL", "Python", "dbt", "PostgreSQL"], "company_rating": 3.9, "industry": "FinTech"},
        {"title": "Analytics Engineer - Data Ops", "company_name": "Uber", "location": "Hyderabad", "experience": "3-6 years", "salary": "₹18,00,000 - ₹28,00,000 PA", "skills": ["SQL", "dbt", "Hive", "Spark"], "company_rating": 4.2, "industry": "Internet"},
        {"title": "Analytics & BI Engineer", "company_name": "Capgemini", "location": "Mumbai", "experience": "2-5 years", "salary": "₹6,00,000 - ₹9,50,000 PA", "skills": ["SQL", "Python", "dbt", "Azure"], "company_rating": 3.9, "industry": "IT Services"},
        {"title": "Analytics Engineer Specialist", "company_name": "Cognizant", "location": "Kochi", "experience": "3-5 years", "salary": "₹7,00,000 - ₹11,00,000 PA", "skills": ["Snowflake", "SQL", "dbt", "ETL"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Associate Analytics Engineer", "company_name": "LTIMindtree", "location": "Chennai", "experience": "1-3 years", "salary": "₹5,00,000 - ₹7,50,000 PA", "skills": ["SQL", "dbt", "PostgreSQL", "Git"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Marketing Analytics Engineer", "company_name": "InMobi", "location": "Bangalore", "experience": "2-4 years", "salary": "₹11,00,000 - ₹16,00,000 PA", "skills": ["SQL", "Python", "dbt", "Fivetran"], "company_rating": 3.9, "industry": "AdTech"},
        {"title": "Lead Analytics Developer", "company_name": "Pine Labs", "location": "Noida", "experience": "5-8 years", "salary": "₹22,00,000 - ₹32,00,000 PA", "skills": ["SQL", "dbt", "Airflow", "Snowflake"], "company_rating": 4.0, "industry": "FinTech"}
    ],
    "Data Scientist": [
        {"title": "Data Scientist - AI & ML", "company_name": "Google", "location": "Bangalore", "experience": "3-6 years", "salary": "₹24,00,000 - ₹36,00,000 PA", "skills": ["Python", "SQL", "TensorFlow", "Scikit-Learn", "Statistics"], "company_rating": 4.6, "industry": "Internet"},
        {"title": "Data Scientist", "company_name": "Microsoft", "location": "Hyderabad", "experience": "2-5 years", "salary": "₹20,00,000 - ₹30,00,000 PA", "skills": ["Python", "PyTorch", "SQL", "Azure", "Machine Learning"], "company_rating": 4.5, "industry": "Software"},
        {"title": "Applied Scientist", "company_name": "Amazon", "location": "Bangalore", "experience": "3-7 years", "salary": "₹26,00,000 - ₹40,00,000 PA", "skills": ["Python", "Machine Learning", "Algorithms", "C++", "SQL"], "company_rating": 4.3, "industry": "E-Commerce"},
        {"title": "Data Scientist - Personalisation", "company_name": "Netflix", "location": "Remote", "experience": "4-8 years", "salary": "₹35,00,000 - ₹55,00,000 PA", "skills": ["Python", "Recommendation Systems", "A/B Testing", "Spark", "SQL"], "company_rating": 4.4, "industry": "Internet"},
        {"title": "Data Scientist - Risk", "company_name": "JPMorgan Chase & Co.", "location": "Mumbai", "experience": "2-4 years", "salary": "₹14,00,000 - ₹21,00,000 PA", "skills": ["Python", "SQL", "R", "Predictive Modeling", "Statistics"], "company_rating": 4.2, "industry": "Financial Services"},
        {"title": "Data Scientist - Customer Analytics", "company_name": "Zomato", "location": "Gurgaon", "experience": "1-3 years", "salary": "₹12,00,000 - ₹18,00,000 PA", "skills": ["Python", "SQL", "Machine Learning", "Pandas", "Matplotlib"], "company_rating": 4.1, "industry": "Internet"},
        {"title": "Data Scientist II", "company_name": "Walmart Global Tech", "location": "Bangalore", "experience": "3-5 years", "salary": "₹18,00,000 - ₹26,00,000 PA", "skills": ["Python", "SQL", "Spark", "Scikit-Learn", "Hive"], "company_rating": 4.2, "industry": "Retail"},
        {"title": "Associate Data Scientist", "company_name": "Myntra", "location": "Bangalore", "experience": "0-2 years", "salary": "₹8,00,000 - ₹13,00,000 PA", "skills": ["Python", "SQL", "Basic ML", "Excel", "Data Analysis"], "company_rating": 4.0, "industry": "E-Commerce"},
        {"title": "Data Scientist - Pricing", "company_name": "Ola Cabs", "location": "Bangalore", "experience": "2-5 years", "salary": "₹11,00,000 - ₹16,00,000 PA", "skills": ["Python", "SQL", "Dynamic Pricing", "Linear Programming"], "company_rating": 3.4, "industry": "Internet"},
        {"title": "Data Scientist - Health Tech", "company_name": "1mg", "location": "Gurgaon", "experience": "1-3 years", "salary": "₹9,00,000 - ₹14,00,000 PA", "skills": ["Python", "SQL", "NLP", "Pandas"], "company_rating": 3.9, "industry": "Healthcare"}
    ],
    "Data Engineer": [
        {"title": "Data Engineer", "company_name": "Meta (Facebook)", "location": "Remote", "experience": "3-6 years", "salary": "₹28,00,000 - ₹42,00,000 PA", "skills": ["SQL", "Python", "Spark", "Hadoop", "Airflow"], "company_rating": 4.3, "industry": "Internet"},
        {"title": "Data Engineer - Pipelines", "company_name": "Swiggy", "location": "Bangalore", "experience": "2-5 years", "salary": "₹14,00,000 - ₹22,00,000 PA", "skills": ["SQL", "Python", "Scala", "Kafka", "Airflow"], "company_rating": 4.0, "industry": "Internet"},
        {"title": "Senior Data Engineer", "company_name": "Uber", "location": "Hyderabad", "experience": "4-8 years", "salary": "₹24,00,000 - ₹35,00,000 PA", "skills": ["SQL", "Python", "Spark", "Flink", "Hadoop"], "company_rating": 4.2, "industry": "Internet"},
        {"title": "Data Engineer Trainee (Fresher)", "company_name": "Cognizant", "location": "Coimbatore", "experience": "0-1 years", "salary": "₹4,00,000 - ₹5,20,000 PA", "skills": ["SQL", "Basic Python", "ETL", "Databases"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Cloud Data Engineer", "company_name": "Wipro", "location": "Bangalore", "experience": "2-4 years", "salary": "₹6,00,000 - ₹9,00,000 PA", "skills": ["SQL", "Python", "AWS", "Glue", "Redshift"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "Big Data Engineer", "company_name": "TCS", "location": "Kolkata", "experience": "3-5 years", "salary": "₹7,00,000 - ₹11,00,000 PA", "skills": ["SQL", "Java", "Hadoop", "Hive", "Spark"], "company_rating": 3.9, "industry": "IT Services"},
        {"title": "Data Engineer - Analytics", "company_name": "Razorpay", "location": "Bangalore", "experience": "2-4 years", "salary": "₹12,00,000 - ₹18,00,000 PA", "skills": ["SQL", "Python", "PostgreSQL", "dbt", "Snowflake"], "company_rating": 4.2, "industry": "FinTech"},
        {"title": "Senior Cloud Data Engineer", "company_name": "Snowflake", "location": "Pune", "experience": "5-8 years", "salary": "₹28,00,000 - ₹44,00,000 PA", "skills": ["Snowflake", "SQL", "Python", "Java", "Airflow"], "company_rating": 4.4, "industry": "Software"},
        {"title": "Data Engineer II", "company_name": "LinkedIn", "location": "Bangalore", "experience": "3-6 years", "salary": "₹20,00,000 - ₹30,00,000 PA", "skills": ["SQL", "Python", "Spark", "Kafka", "Data Modeling"], "company_rating": 4.3, "industry": "Internet"},
        {"title": "Associate Data Engineer", "company_name": "EY", "location": "Noida", "experience": "1-3 years", "salary": "₹5,00,000 - ₹7,80,000 PA", "skills": ["SQL", "Python", "SSIS", "Data Warehousing"], "company_rating": 3.9, "industry": "Accounting"}
    ],
    "Machine Learning Engineer": [
        {"title": "Machine Learning Engineer", "company_name": "Google", "location": "Bangalore", "experience": "3-6 years", "salary": "₹26,00,000 - ₹38,00,000 PA", "skills": ["Python", "TensorFlow", "Kubernetes", "Docker", "PyTorch"], "company_rating": 4.6, "industry": "Internet"},
        {"title": "ML Engineer - NLP", "company_name": "OpenAI", "location": "Remote", "experience": "4-8 years", "salary": "₹45,00,000 - ₹75,00,000 PA", "skills": ["Python", "PyTorch", "NLP", "Transformers", "Distributed Systems"], "company_rating": 4.8, "industry": "Artificial Intelligence"},
        {"title": "MLOps Engineer", "company_name": "Microsoft", "location": "Hyderabad", "experience": "3-5 years", "salary": "₹22,00,000 - ₹33,00,000 PA", "skills": ["Python", "Azure ML", "CI/CD", "MLflow", "Docker"], "company_rating": 4.5, "industry": "Software"},
        {"title": "Applied ML Engineer", "company_name": "Amazon", "location": "Bangalore", "experience": "2-5 years", "salary": "₹18,00,000 - ₹28,00,000 PA", "skills": ["Python", "SQL", "Scikit-Learn", "SageMaker", "AWS"], "company_rating": 4.3, "industry": "E-Commerce"},
        {"title": "ML Engineer - Computer Vision", "company_name": "Samsung Research", "location": "Bangalore", "experience": "2-5 years", "salary": "₹14,00,000 - ₹22,00,000 PA", "skills": ["Python", "OpenCV", "PyTorch", "C++", "Deep Learning"], "company_rating": 4.0, "industry": "Hardware"},
        {"title": "Machine Learning Engineer", "company_name": "Flipkart", "location": "Bangalore", "experience": "2-4 years", "salary": "₹13,00,000 - ₹20,00,000 PA", "skills": ["Python", "SQL", "XGBoost", "Pandas", "Scikit-Learn"], "company_rating": 4.0, "industry": "E-Commerce"},
        {"title": "Junior ML Engineer", "company_name": "Infosys", "location": "Pune", "experience": "1-3 years", "salary": "₹5,00,000 - ₹8,00,000 PA", "skills": ["Python", "SQL", "Scikit-Learn", "Matplotlib"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Machine Learning Analyst", "company_name": "Cognizant", "location": "Chennai", "experience": "0-2 years", "salary": "₹4,50,000 - ₹6,50,000 PA", "skills": ["Python", "Excel", "Data Prep", "SQL"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "Senior ML Infrastructure Engineer", "company_name": "Intel", "location": "Bangalore", "experience": "5-8 years", "salary": "₹28,00,000 - ₹40,00,000 PA", "skills": ["C++", "Python", "CUDA", "TensorRT", "Deep Learning"], "company_rating": 4.1, "industry": "Hardware"},
        {"title": "Machine Learning Engineer - FinTech", "company_name": "Paytm", "location": "Noida", "experience": "2-4 years", "salary": "₹10,00,000 - ₹16,00,000 PA", "skills": ["Python", "SQL", "Anomaly Detection", "Scikit-Learn"], "company_rating": 3.5, "industry": "FinTech"}
    ],
    "BI Developer": [
        {"title": "BI Developer (Power BI)", "company_name": "Accenture", "location": "Bangalore", "experience": "2-4 years", "salary": "₹6,00,000 - ₹9,50,000 PA", "skills": ["Power BI", "DAX", "SQL", "Data Warehousing"], "company_rating": 4.1, "industry": "Consulting"},
        {"title": "BI Developer - Tableau Specialist", "company_name": "Capgemini", "location": "Mumbai", "experience": "2-5 years", "salary": "₹5,80,000 - ₹8,50,000 PA", "skills": ["Tableau", "SQL", "ETL", "Excel"], "company_rating": 3.9, "industry": "IT Services"},
        {"title": "Senior BI Developer", "company_name": "Dell Technologies", "location": "Bangalore", "experience": "4-7 years", "salary": "₹12,00,000 - ₹18,00,000 PA", "skills": ["SQL", "SSAS", "SSIS", "Tableau", "Power BI"], "company_rating": 4.2, "industry": "Hardware"},
        {"title": "BI Developer Trainee", "company_name": "Wipro", "location": "Chennai", "experience": "0-1 years", "salary": "₹3,50,000 - ₹4,80,000 PA", "skills": ["SQL", "Excel", "Data Visualisation", "Basic Reporting"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "BI Specialist", "company_name": "LTIMindtree", "location": "Pune", "experience": "3-6 years", "salary": "₹7,50,000 - ₹11,00,000 PA", "skills": ["SQL", "QlikView", "Power BI", "Data Modeling"], "company_rating": 3.8, "industry": "IT Services"},
        {"title": "BI Developer - Business Insights", "company_name": "HCLTech", "location": "Noida", "experience": "1-3 years", "salary": "₹4,50,000 - ₹6,80,000 PA", "skills": ["SQL", "Tableau", "Excel", "Data Integration"], "company_rating": 3.7, "industry": "IT Services"},
        {"title": "BI Developer II", "company_name": "Cisco", "location": "Bangalore", "experience": "3-5 years", "salary": "₹14,00,000 - ₹21,00,000 PA", "skills": ["SQL", "Power BI", "Snowflake", "Looker"], "company_rating": 4.3, "industry": "Hardware"},
        {"title": "BI Consultant", "company_name": "EY", "location": "Hyderabad", "experience": "2-4 years", "salary": "₹7,00,000 - ₹10,50,000 PA", "skills": ["SQL", "Power BI", "Tableau", "Client Reporting"], "company_rating": 3.9, "industry": "Accounting"},
        {"title": "BI Engineer", "company_name": "Swiggy", "location": "Bangalore", "experience": "3-5 years", "salary": "₹12,00,000 - ₹17,00,000 PA", "skills": ["SQL", "Looker", "Redshift", "Python"], "company_rating": 4.0, "industry": "Internet"},
        {"title": "BI Developer - Financial Systems", "company_name": "JPMorgan Chase & Co.", "location": "Mumbai", "experience": "3-6 years", "salary": "₹15,00,000 - ₹22,00,000 PA", "skills": ["SQL", "Oracle", "Excel", "Tableau", "Cognos"], "company_rating": 4.2, "industry": "Financial Services"}
    ],
    "Product Analyst": [
        {"title": "Product Analyst", "company_name": "Zomato", "location": "Gurgaon", "experience": "1-3 years", "salary": "₹9,00,000 - ₹14,00,000 PA", "skills": ["SQL", "Python", "Google Analytics", "A/B Testing"], "company_rating": 4.1, "industry": "Internet"},
        {"title": "Product Analyst - Growth", "company_name": "Swiggy", "location": "Bangalore", "experience": "2-4 years", "salary": "₹11,00,000 - ₹16,00,000 PA", "skills": ["SQL", "Python", "Amplitude", "Mixpanel", "A/B Testing"], "company_rating": 4.0, "industry": "Internet"},
        {"title": "Product Analyst (Fresher/Trainee)", "company_name": "Paytm", "location": "Noida", "experience": "0-1 years", "salary": "₹5,00,000 - ₹7,00,000 PA", "skills": ["SQL", "Excel", "Analytical Mindset", "Data Cleaning"], "company_rating": 3.5, "industry": "FinTech"},
        {"title": "Product Analyst - Search & Discovery", "company_name": "Flipkart", "location": "Bangalore", "experience": "2-5 years", "salary": "₹12,00,000 - ₹18,00,000 PA", "skills": ["SQL", "Python", "Tableau", "Product Metrics"], "company_rating": 4.0, "industry": "E-Commerce"},
        {"title": "Senior Product Analyst", "company_name": "Uber", "location": "Hyderabad", "experience": "3-6 years", "salary": "₹18,00,000 - ₹26,00,000 PA", "skills": ["SQL", "Python", "A/B Testing", "Mixpanel", "Statistics"], "company_rating": 4.2, "industry": "Internet"},
        {"title": "Product Analyst - Payments", "company_name": "Razorpay", "location": "Remote", "experience": "1-3 years", "salary": "₹8,00,000 - ₹13,00,000 PA", "skills": ["SQL", "Excel", "Python", "Tableau"], "company_rating": 4.2, "industry": "FinTech"},
        {"title": "Product Strategy Analyst", "company_name": "Adobe", "location": "Bangalore", "experience": "2-5 years", "salary": "₹15,00,000 - ₹23,00,000 PA", "skills": ["SQL", "Python", "Product Analytics", "Tableau"], "company_rating": 4.4, "industry": "Software"},
        {"title": "Product Analyst II", "company_name": "Netflix", "location": "Mumbai", "experience": "3-6 years", "salary": "₹28,00,000 - ₹42,00,000 PA", "skills": ["SQL", "Python", "A/B Testing", "Amplitude"], "company_rating": 4.4, "industry": "Internet"},
        {"title": "Associate Product Analyst", "company_name": "Cred", "location": "Bangalore", "experience": "0-2 years", "salary": "₹7,50,000 - ₹11,00,000 PA", "skills": ["SQL", "Excel", "Google Analytics"], "company_rating": 3.9, "industry": "FinTech"},
        {"title": "Product Data Analyst", "company_name": "InMobi", "location": "Bangalore", "experience": "2-4 years", "salary": "₹10,00,000 - ₹15,00,000 PA", "skills": ["SQL", "Python", "Tableau", "Excel"], "company_rating": 3.9, "industry": "AdTech"}
    ],
    "Quantitative Analyst": [
        {"title": "Quantitative Research Analyst", "company_name": "JPMorgan Chase & Co.", "location": "Mumbai", "experience": "3-6 years", "salary": "₹22,00,000 - ₹34,00,000 PA", "skills": ["Python", "SQL", "Stochastic Calculus", "R", "Quantitative Finance"], "company_rating": 4.2, "industry": "Financial Services"},
        {"title": "Quantitative Trader", "company_name": "Goldman Sachs", "location": "Bangalore", "experience": "2-5 years", "salary": "₹25,00,000 - ₹40,00,000 PA", "skills": ["Python", "Algorithms", "C++", "Statistics", "Machine Learning"], "company_rating": 4.1, "industry": "Financial Services"},
        {"title": "Risk Quant Analyst", "company_name": "HSBC", "location": "Bangalore", "experience": "3-5 years", "salary": "₹16,00,000 - ₹24,00,000 PA", "skills": ["Python", "SQL", "Quantitative Risk", "Excel", "SAS"], "company_rating": 3.9, "industry": "Banking"},
        {"title": "Quantitative Analyst", "company_name": "Morgan Stanley", "location": "Mumbai", "experience": "2-5 years", "salary": "₹18,00,000 - ₹28,00,000 PA", "skills": ["Python", "SQL", "C++", "R", "Financial Modeling"], "company_rating": 4.3, "industry": "Financial Services"},
        {"title": "Quantitative Research Associate", "company_name": "Barclays", "location": "Pune", "experience": "2-4 years", "salary": "₹14,00,000 - ₹21,00,000 PA", "skills": ["Python", "SQL", "Statistics", "Time Series Analysis"], "company_rating": 4.0, "industry": "Banking"},
        {"title": "Quantitative Analyst - Derivatives", "company_name": "Citigroup", "location": "Mumbai", "experience": "3-6 years", "salary": "₹17,00,000 - ₹26,00,000 PA", "skills": ["Python", "C++", "SQL", "Derivatives Pricing"], "company_rating": 4.0, "industry": "Banking"},
        {"title": "Junior Quantitative Analyst", "company_name": "Standard Chartered Bank", "location": "Chennai", "experience": "0-2 years", "salary": "₹8,00,000 - ₹12,00,000 PA", "skills": ["Python", "SQL", "Excel", "Mathematics"], "company_rating": 3.8, "industry": "Banking"},
        {"title": "Quantitative Portfolio Analyst", "company_name": "BlackRock", "location": "Gurgaon", "experience": "3-6 years", "salary": "₹20,00,000 - ₹30,00,000 PA", "skills": ["Python", "SQL", "Portfolio Optimisation", "R"], "company_rating": 4.2, "industry": "Financial Services"},
        {"title": "Quantitative Analyst - High Frequency", "company_name": "Tower Research Capital", "location": "Gurgaon", "experience": "3-7 years", "salary": "₹35,00,000 - ₹55,00,000 PA", "skills": ["C++", "Python", "Algorithms", "Linear Algebra"], "company_rating": 4.5, "industry": "Proprietary Trading"},
        {"title": "Quant Risk Analyst - Fresh Graduate", "company_name": "Deutsche Bank", "location": "Pune", "experience": "0-1 years", "salary": "₹7,50,000 - ₹11,00,000 PA", "skills": ["Python", "Excel", "SQL", "Probability"], "company_rating": 3.9, "industry": "Banking"}
    ]
}

# ---------------------------------------------------------------------------
# Network Helpers (Rotated User-Agents / Delay logic kept for compatibility)
# ---------------------------------------------------------------------------
def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

def get_random_delay(min_sec: float = 1.0, max_sec: float = 3.5) -> None:
    time.sleep(random.uniform(min_sec, max_sec))

def request_page(session: requests.Session, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    for attempt in range(1, retries + 1):
        try:
            get_random_delay()
            headers = get_headers()
            logger.info("Fetching URL (Attempt %d/%d): %s", attempt, retries, url)
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            try:
                return BeautifulSoup(response.content, "lxml")
            except Exception:
                return BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as exc:
            logger.warning("Request failed (attempt %d): %s", attempt, exc)
            time.sleep(2 ** (attempt - 1))
    return None

def parse_salary(salary_text: str) -> str:
    return salary_text.strip() if salary_text else "Not Disclosed"

def extract_skills(skills_text: str) -> List[str]:
    if not skills_text:
        return []
    raw = [s.strip() for s in skills_text.replace("\n", ",").split(",")]
    seen = set()
    unique = []
    for skill in raw:
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            unique.append(skill)
    return unique

def parse_date(date_text: str) -> Optional[str]:
    if not date_text:
        return None
    text = date_text.lower().strip()
    today = datetime.now()
    try:
        if any(kw in text for kw in ("today", "few hours", "just now")):
            return today.strftime("%Y-%m-%d")
        digits = re.findall(r"\d+", text)
        count = int(digits[0]) if digits else 1
        if "day" in text:
            return (today - timedelta(days=count)).strftime("%Y-%m-%d")
        if "month" in text:
            return (today - timedelta(days=count * 30)).strftime("%Y-%m-%d")
        if "week" in text:
            return (today - timedelta(weeks=count)).strftime("%Y-%m-%d")
        return today.strftime("%Y-%m-%d")
    except Exception:
        return today.strftime("%Y-%m-%d")

def _generate_job_id(title: str, company: str) -> str:
    raw = f"{title}|{company}".lower().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]

def scrape_naukri(job_role: str, max_pages: int = 1) -> List[Dict[str, Any]]:
    slug = job_role.lower().replace(" ", "-")
    base_url = f"https://www.naukri.com/{slug}-jobs-{{page}}"
    extracted = []
    with requests.Session() as session:
        for page in range(1, max_pages + 1):
            url = base_url.format(page=page)
            soup = request_page(session, url)
            if not soup:
                break
            cards = soup.select(_CARD_SELECTORS)
            if not cards:
                break
            for card in cards:
                # Basic parsing placeholder structure (live site bypasses requests)
                pass
    return extracted

def save_jobs_to_database(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"inserted": 0, "duplicates": 0, "errors": 0}
    seen_ids = set()
    for job in jobs:
        job_id = job.get("job_id")
        if not job_id:
            stats["errors"] += 1
            continue
        if job_id in seen_ids:
            stats["duplicates"] += 1
            continue
        seen_ids.add(job_id)

        db_payload = {
            "job_id": job_id,
            "title": job.get("title"),
            "company_name": job.get("company_name"),
            "industry": job.get("industry"),
            "company_rating": job.get("company_rating"),
            "location": job.get("location"),
            "experience": job.get("experience"),
            "salary": job.get("salary"),
            "posted_date": job.get("posted_date"),
            "skills": job.get("skills", []),
        }
        if database.insert_job(db_payload):
            stats["inserted"] += 1
            # Maintain backward compatibility with the raw skills frequency counter table
            for skill in job.get("skills", []):
                database.insert_skill(skill)
        else:
            stats["errors"] += 1
    return stats

def run_full_scraper() -> None:
    """Run the complete scraping workflow, populating 100+ jobs via simulation fallback."""
    all_jobs = []
    start = time.time()

    # 1. Try Live Scraping
    for role in TARGET_ROLES:
        logger.info("--- Attempting Live Scrape: %s ---", role)
        jobs = scrape_naukri(role, max_pages=MAX_PAGES_PER_ROLE)
        all_jobs.extend(jobs)

    # 2. Trigger Simulated Database Seeding
    is_simulated = False
    if not all_jobs:
        logger.warning("Live scraping returned 0 jobs. Seeding root jobs.db with 100+ simulated jobs...")
        is_simulated = True
        
        for role, job_list in SIMULATED_JOBS.items():
            for index, mock_job in enumerate(job_list):
                # Unique job title per entry to avoid name clashes
                job_id = _generate_job_id(mock_job["title"] + str(index), mock_job["company_name"])
                posted_date = (datetime.now() - timedelta(days=index % 14)).strftime("%Y-%m-%d")
                
                all_jobs.append({
                    "job_id": job_id,
                    "title": mock_job["title"],
                    "company_name": mock_job["company_name"],
                    "location": mock_job["location"],
                    "experience": mock_job["experience"],
                    "salary": mock_job["salary"],
                    "skills": mock_job["skills"],
                    "posted_date": posted_date,
                    "company_rating": mock_job["company_rating"],
                    "industry": mock_job["industry"],
                })

    # 3. Persist
    stats = save_jobs_to_database(all_jobs)
    
    # 4. Generate Snapshot Metrics
    try:
        total_active = len(all_jobs)
        avg_salary = 1520000.0  # Combined baseline average of the 10 expanded profiles
        for days_back in range(14):
            snap_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            daily_variation = random.uniform(-100000, 100000) if is_simulated else 0
            database.update_daily_snapshot({
                "snapshot_date": snap_date,
                "total_active_jobs": total_active - (days_back if is_simulated else 0),
                "new_jobs_added": random.randint(5, 12) if is_simulated else 0,
                "top_hiring_sectors": "FinTech, Software, Consulting",
                "avg_salary_offered": avg_salary + daily_variation,
            })
    except Exception as exc:
        logger.warning("Could not populate snapshots: %s", exc)

    scrape_secs = time.time() - start
    print("\n" + "=" * 50)
    print("        DATABASE POPULATE REPORT")
    print("=" * 50)
    print(f"  Job Profiles Created : {len(TARGET_ROLES)}")
    print(f"  Total Jobs Seeded    : {len(all_jobs)}")
    print(f"  Inserted / Updated   : {stats['inserted']}")
    print(f"  Duplicates Skipped   : {stats['duplicates']}")
    print(f"  Errors / Skips       : {stats['errors']}")
    print(f"  Execution Time       : {scrape_secs:.2f}s")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    database.create_database()
    run_full_scraper()
