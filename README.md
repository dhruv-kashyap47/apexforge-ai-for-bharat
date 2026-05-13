# ApexForge AI

ApexForge AI is a Streamlit-based business identity resolution system. It helps clean messy business records, detect likely duplicates, group related entries, and assign a Unified Business Identity (UBID) to records that appear to belong to the same business.

## What it does

* Cleans and standardizes business data from CSV files
* Validates common identifiers such as PAN and GSTIN
* Analyzes business status based on available activity data
* Matches likely duplicate records using exact and fuzzy logic
* Groups related records into a single business identity
* Generates UBIDs for matched business groups
* Provides dashboards, review queues, analytics, and graph views
* Optionally uses AI to help explain matches and support natural-language filtering

## Why it exists

Business data often comes from multiple sources and appears with inconsistent spelling, formatting, missing identifiers, or partial details. ApexForge AI helps reduce manual cleanup and gives teams a single place to inspect and manage linked records.

## Core workflow

1. Upload a CSV file
2. Clean and normalize the data
3. Analyze status and quality signals
4. Find exact and fuzzy matches
5. Group records into business clusters
6. Generate UBIDs
7. Review results in the dashboard, network graph, and review queue

## Project structure

* `app.py` — Streamlit app entry point and page routing
* `core/` — data cleaning, matching, status analysis, and UBID generation
* `services/` — data storage, visualization, and optional AI support
* `db/` — database connection and schema helpers
* `sample csv/` — example input files

## Main modules

### `core/data_cleaner.py`

Normalizes text fields, validates identifiers, and prepares the input for matching.

### `core/status_analyzer.py`

Assigns business lifecycle states such as Active, Dormant, or Closed using the available date and activity fields.

### `core/matching_engine.py`

Finds exact and fuzzy matches, then groups related records.

### `core/ubid_generator.py`

Creates UBIDs for grouped records and checks for collisions within the current run or database context.

### `services/data_service.py`

Handles storage and retrieval of processed results.

### `services/visualization_service.py`

Builds graph-style views for record relationships.

### `services/ai_service.py`

Provides optional AI-based explanations and natural-language query parsing.

### `db/connection.py`

Manages optional PostgreSQL connectivity.

## Features

* CSV upload and processing
* Data quality summary
* Status analysis
* Exact and fuzzy matching
* Review queue for uncertain matches
* UBID explorer
* Network visualization
* Optional AI-assisted explanations and search
* Optional PostgreSQL persistence

## UBID format

The UBID follows a structured format such as:

```text
KA-BAN-TR-4829103
```

Where the parts represent location and category information, followed by a generated numeric suffix.

## Match tiers

* **Tier 1** — Exact identifier match, such as PAN or GSTIN
* **Tier 2** — Strong name and location similarity
* **Tier 3** — Moderate similarity that may need human review
* **New** — No reliable match found

## Confidence handling

Matches are assigned confidence values to help with review:

* High confidence records can be auto-merged
* Medium confidence records should be reviewed
* Low confidence records should stay separate unless verified

## Optional AI features

If configured, the app can use AI for:

* Explaining why two records matched
* Summarizing data quality
* Interpreting natural-language filters on the results page

The core matching pipeline does not depend on AI and can run without it.

## Local setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file if needed:

```env
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/apexforge_db
```

Both are optional. The app can run without them.

### 3. Run the app

```bash
streamlit run app.py
```

## Sample usage

1. Open the app in your browser
2. Upload a CSV file
3. Click the process button
4. Review the dashboard and results
5. Inspect uncertain matches in the review queue
6. Explore groups in the network graph or UBID explorer

## Data expectations

The app works best when the input contains some combination of:

* business name
* PAN
* GSTIN
* address fields
* pincode
* state
* district
* activity or date fields

Missing fields are handled where possible, but better input gives better matching results.

## Limitations

This project is designed as an MVP and demo-ready system.

Important limitations:

* Large files may require chunked or background processing
* Fuzzy matching can become expensive on very large datasets
* Visual graphs may not scale well to extremely large record sets
* AI features depend on external service availability if enabled
* Human review is still needed for uncertain matches

## Security and reliability notes

* Validate and sanitize uploaded CSV input before processing
* Keep API keys in environment variables, not in code
* Use parameterized database queries
* Treat AI-generated explanations as advisory, not authoritative
* Review uncertain matches before final approval

## Recommended production improvements

* Split `app.py` into smaller page modules
* Add background jobs for heavy processing
* Use chunked ingestion for large uploads
* Add stronger audit logs and merge reversal support
* Add performance benchmarks with real datasets
* Replace ad hoc scaling assumptions with measured profiling results

## Acknowledgements

Built as a business identity resolution and record-linking system for messy, multi-source data.
