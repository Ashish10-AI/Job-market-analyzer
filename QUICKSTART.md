# ⚡ Quickstart Guide

Get the Job Market Intelligence Platform running locally in under 2 minutes.

## 📋 Prerequisites
- **Python 3.8+** installed on your system.
- **Git** for repository cloning.
- Basic terminal access (Command Prompt, PowerShell, or Bash).

---

## 🛠️ Setup Instructions

### 1. Clone the Repository
Open your terminal and clone the repository:
```bash
git clone https://github.com/yourusername/job-market-intelligence.git
cd job-market-intelligence
```

### 2. Environment Configuration
It is highly recommended to isolate the project dependencies using a virtual environment. Run the commands exactly as provided in `SETUP_COMMANDS.txt`:

```bash
# Initialize Virtual Environment
python -m venv venv

# Activate Environment (Windows)
venv\Scripts\activate
# Activate Environment (macOS/Linux)
source venv/bin/activate

# Install Required Packages
pip install -r requirements.txt
```

### 3. Initialize the Database & Fetch Data
The SQLite database will be automatically created on its first run. Execute the scraper to fetch your first batch of market intelligence:
```bash
python scraper.py
```
*Wait for the terminal summary to display a successful ingestion count.*

### 4. Launch the Dashboard
Start the interactive Streamlit server:
```bash
streamlit run app.py
```
*Your browser will automatically open to `http://localhost:8501`.*

---

## 🎯 Next Steps
- Open the dashboard and explore the **Skills Analysis** and **Action Plan** tabs.
- Click the **Download Executive Report (PDF)** button in the sidebar to test the PDF generation capability.
- Check the `reports/` folder to view your newly generated files.
