# 🏢 ApexForge AI — Unified Business Identity System

A **production-ready**, end-to-end application for **automated business identity resolution** and **duplicate detection**. Built with Python, PostgreSQL, Streamlit, and PyVis.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.29+-red.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 What It Does

**Zero-manual-step** business identity resolution system:

1. **📁 Upload CSV** → Automatic data ingestion
2. **🧹 Clean Data** → Normalize names, PANs, GSTINs, addresses
3. **🔗 Match Duplicates** → AI-powered fuzzy matching with tiered logic
4. **🆔 Assign UBID** → Generate unique Unified Business IDs
5. **📊 Calculate Confidence** → Score-based match decisions
6. **🚦 Determine Status** → Active / Dormant / Closed classification
7. **🕸️ Visualize Network** → Interactive graph of matches
8. **📈 View Dashboard** → Complete analytics and insights
9. **💾 Store Results** → Persistent PostgreSQL storage

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+ (local or cloud)
- 2GB RAM minimum

### 1. Clone & Setup

```bash
# Navigate to project directory
cd apexforge-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/apexforge_db
```

Or use individual variables:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=apexforge_db
DB_USER=your_username
DB_PASSWORD=your_password
```

**Create the database:**

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE apexforge_db;

# Exit
\q
```

### 3. Run the Application

```bash
streamlit run app.py
```

The app will open at: **http://localhost:8501**

---

## � Security Best Practices

### ⚠️ IMPORTANT: Never Commit Secrets!

This repository includes security checks to prevent accidental exposure of sensitive credentials.

### Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your real credentials** (this file is gitignored and will never be committed)

3. **Install the pre-commit hook** (optional but recommended):
   ```bash
   cp pre-commit-hook.sh .git/hooks/pre-commit
   # On Windows with Git Bash:
   chmod +x .git/hooks/pre-commit
   ```

### Running Security Checks

Before committing, run the security scanner:

```bash
python security_check.py
```

This checks for:
- ✅ `.env` is properly gitignored
- ✅ No hardcoded passwords or API keys in code
- ✅ `.env.example` uses placeholder values
- ✅ No private keys or certificates

### What Gets Protected

The `.gitignore` automatically excludes:
- `.env` files (all variants)
- SSH keys (`*.pem`, `*.key`)
- Database files (`*.db`, `*.sqlite`)
- Python cache (`__pycache__/`, `*.pyc`)
- Virtual environments (`venv/`, `.venv/`)

---

## �📂 Project Structure

```
apexforge-ai/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── schema.sql                  # PostgreSQL database schema
├── .env.example              # Environment variables template
├── README.md                 # This file
│
├── db/                       # Database layer
│   ├── __init__.py
│   └── connection.py         # SQLAlchemy connection manager
│
├── core/                     # Core business logic
│   ├── __init__.py
│   ├── data_cleaner.py       # Data cleaning & normalization
│   ├── matching_engine.py    # Fuzzy matching algorithm
│   ├── ubid_generator.py     # UBID generation logic
│   └── status_analyzer.py    # Business status classification
│
├── services/                 # Service layer
│   ├── __init__.py
│   ├── data_service.py       # Data operations
│   ├── match_service.py      # Match processing
│   └── visualization_service.py  # PyVis network graphs
│
└── utils/                    # Utilities
    ├── __init__.py
    └── helpers.py            # Helper functions
```

---

## 📋 CSV Input Format

Your CSV file **must** contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `business_name` | Legal business name | Tech Solutions Pvt Ltd |
| `pan` | 10-character PAN | ABCPE1234F |
| `gstin` | 15-character GSTIN | 27ABCPE1234F1Z5 |
| `address` | Full address | 123 Main Road, Mumbai |
| `pincode` | 6-digit PIN | 400001 |
| `district` | District name | Mumbai |
| `state` | State name | Maharashtra |
| `registration_date` | Date of registration | 2020-01-15 |
| `last_activity_date` | Last known activity | 2024-01-10 |
| `department` | Source department | GST, Income Tax |

### Sample CSV

```csv
business_name,pan,gstin,address,pincode,district,state,registration_date,last_activity_date,department
Tech Solutions Pvt Ltd,ABCPE1234F,27ABCPE1234F1Z5,123 Main Road Mumbai,400001,Mumbai,Maharashtra,2020-01-15,2024-01-10,GST
Global Traders,XYZPK5678L,29XYZPK5678L1Z8,456 Market Street Bangalore,560001,Bangalore,Karnataka,2019-06-20,2023-12-01,Income Tax
```

**Generate sample data**: Use the in-app "Generate Sample CSV" feature on the Upload page.

---

## ⚙️ Matching Logic

### Tier 1 — Exact Match (100% Confidence)
- **PAN match** OR **GSTIN match** → Auto-merge

### Tier 2 — Strong Match (80-100% Confidence)
- Name similarity > **80%** using RapidFuzz
- AND same **pincode** OR **district**
- Decision: Auto-merge (≥85%) or Needs Review (80-84%)

### Tier 3 — Weak Match (50-80% Confidence)
- Name similarity **50-80%**
- Decision: Needs manual review

### No Match (<50%)
- Keep as separate entity with new UBID

---

## 🆔 UBID Format

**Structure:** `STATE-DISTRICT-CATEGORY-SEQUENCE`

**Example:** `MH-MUM-TR-0004123`

| Component | Description | Example |
|-----------|-------------|---------|
| STATE | 2-letter state code | MH, KA, DL |
| DISTRICT | 3-letter district code | MUM, BAN, ND |
| CATEGORY | Business category | TR (Trading), MF (Manufacturing), SV (Services) |
| SEQUENCE | 7-digit unique number | 0004123 |

---

## 📊 Confidence Scoring

| Score Range | Action | Badge |
|-------------|--------|-------|
| **85-100%** | Auto Merge | 🟢 Green |
| **50-84%** | Needs Review | 🟡 Yellow |
| **<50%** | Keep Separate | 🔴 Red |

---

## 🚦 Business Status Logic

| Status | Definition | Criteria |
|--------|------------|----------|
| **🟢 Active** | Currently operating | Activity in last 12 months |
| **🟡 Dormant** | Temporarily inactive | No activity for 12-18 months |
| **🔴 Closed** | Ceased operations | No activity for 18+ months |

---

## 🖥️ UI Pages

### 1. 📁 Upload Data
- Drag-and-drop CSV upload
- Data validation and preview
- Sample CSV generator

### 2. 📊 Dashboard
- Processing statistics
- Real-time metrics
- Status distribution charts

### 3. 🔍 Results Table
- Filterable, searchable data grid
- Export to CSV
- Match tier badges

### 4. 🕸️ Network Graph
- **Interactive PyVis visualization**
- Color-coded nodes by match tier
- Edge strength indicates match confidence
- Zoom, pan, and click interactions

### 5. 🔎 UBID Explorer
- Search by UBID, name, PAN, GSTIN
- View linked records
- Business identity details

### 6. ⚖️ Review Queue
- Approve/reject weak matches
- Side-by-side record comparison
- Audit trail with notes

### 7. 📈 Analytics
- System-wide statistics
- Processing history
- Match quality metrics

---

## 🗄️ Database Schema

### Tables

1. **`raw_records`** — All uploaded business data
2. **`matched_groups`** — Groups of matched records
3. **`ubid_registry`** — Central UBID registry
4. **`match_logs`** — Audit trail of matching decisions
5. **`review_queue`** — Pending manual reviews

### Key Features
- Full audit trail
- Soft delete support
- Optimized indexes
- JSONB for flexible metadata

**Initialize schema:**
```sql
psql -d apexforge_db -f schema.sql
```

---

## 🧪 Testing

### Generate Sample Data
1. Go to **Upload Data** page
2. Click "Generate Sample CSV"
3. Download and re-upload to test

### Verify Installation
```bash
python -c "import streamlit, pandas, psycopg2, sqlalchemy, rapidfuzz, pyvis; print('✅ All imports successful')"
```

### Test Database Connection
```bash
python -c "from db.connection import get_db_manager; db = get_db_manager(); print('✅ Database connected')"
```

---

## 🛠️ Development

### Add New Features

1. **Core Logic**: Add to `core/` modules
2. **Database**: Update `schema.sql` and `db/connection.py`
3. **Services**: Implement in `services/`
4. **UI**: Add page functions in `app.py`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `APP_TITLE` | Application title | No |
| `DEBUG` | Enable debug mode | No |

---

## 📦 Deployment

### Local
```bash
streamlit run app.py
```

### Production Server
```bash
# Using nohup
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# Using systemd (create service file)
sudo systemctl enable apexforge
sudo systemctl start apexforge
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Cloud Platforms

**Streamlit Cloud:**
1. Push to GitHub
2. Connect to [share.streamlit.io](https://share.streamlit.io)
3. Add `DATABASE_URL` to secrets

**Heroku:**
```bash
heroku create apexforge-ai
heroku addons:create heroku-postgresql:mini
heroku config:set DATABASE_URL=$(heroku config:get DATABASE_URL)
git push heroku main
```

---

## 🎓 Demo Steps

1. **Start the app**: `streamlit run app.py`
2. **Initialize DB**: Click "Initialize Database" button
3. **Generate sample**: Click "Generate Sample CSV" → Download
4. **Upload data**: Drag CSV to upload area → Click "Process Data"
5. **View dashboard**: See real-time statistics
6. **Explore results**: Check Results table with filters
7. **View network graph**: See interactive match visualization
8. **Review matches**: Approve/reject weak matches in Review Queue

---

## 🔒 Security

- Database credentials in `.env` (never commit)
- SQL injection protection via SQLAlchemy ORM
- Input validation on all uploads
- No sensitive data in logs

---

## 🐛 Troubleshooting

### "Database connection failed"
- Verify PostgreSQL is running
- Check DATABASE_URL format
- Ensure database exists

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Permission denied"
- Check PostgreSQL user privileges
- Grant CREATE, INSERT, SELECT permissions

### "Visualization not loading"
- Ensure JavaScript is enabled in browser
- Try refreshing the Network Graph page

---

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs in the terminal
3. Verify database connectivity

---

## 📄 License

MIT License - feel free to use for commercial and personal projects.

---

## 🙏 Credits

- **Streamlit** — UI framework
- **PyVis** — Network visualization
- **RapidFuzz** — Fast string matching
- **SQLAlchemy** — Database ORM
- **PostgreSQL** — Reliable data storage

---

**Built with ❤️ for the business identity resolution challenge.**
